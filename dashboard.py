#!/usr/bin/env python3
"""
Dashboard: Generator Aukcji Produktowych v3.2
Klient: Granitowe Zlewy (Marcin Mysliwiec)
Stack: Streamlit + Gemini API + BaseLinker API
Multi-katalog: Granitowe Zlewy + Oswietlenie LED
"""

import hmac
import html as html_lib
import io
import os
import re
import time
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

from config import get_secret as _get_secret, MODEL

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    import PIL.Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from catalogs import get_catalog_display_names, get_categories, get_kolor_map, get_kolory_per_element
from prompts import (
    get_image_prompts, generate_description_prompt, parse_description_sections,
    get_description_revision_prompt, check_ban_list,
)
from baselinker import send_to_baselinker, check_sku_exists
from extraction import extract_spec_data
from history import save_generation, load_history, cleanup_old_outputs

try:
    from prompts import get_regen_prompt
    REGEN_AVAILABLE = True
except ImportError:
    REGEN_AVAILABLE = False

# ---------------------------------------------------------------------------
# Konfiguracja
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

# ---------------------------------------------------------------------------
# Styl strony
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Generator Aukcji · GranitoweZlewy",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

_css_path = BASE_DIR / "dashboard_styles.css"
if _css_path.exists():
    with open(_css_path, "r", encoding="utf-8") as _f:
        st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)
else:
    st.warning("Brak pliku dashboard_styles.css")


# ---------------------------------------------------------------------------
# Password gate (opcjonalny)
# ---------------------------------------------------------------------------

_app_password = _get_secret("APP_PASSWORD", "")
if _app_password:
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "login_attempts" not in st.session_state:
        st.session_state["login_attempts"] = 0
        st.session_state["lockout_until"] = 0.0
    if not st.session_state["authenticated"]:
        # A9: Login screen branding
        st.markdown("""
<div style="max-width:360px;margin:60px auto;text-align:center;">
    <div class="gz-badge" style="margin:0 auto 24px;width:fit-content;">
        <div class="gz-badge-dot"></div>
        <span style="font-size:12px;font-weight:600;color:#a8893e;">GranitoweZlewy</span>
    </div>
    <h2 style="font-size:22px;font-weight:700;margin-bottom:24px;color:#1d1d1f;">Generator Aukcji</h2>
</div>
""", unsafe_allow_html=True)
        if time.time() < st.session_state["lockout_until"]:
            remaining = int(st.session_state["lockout_until"] - time.time())
            st.error(f"Za dużo prób. Odczekaj {remaining} sekund.")
            st.stop()
        pwd = st.text_input("Hasło dostępu", type="password")
        if st.button("Zaloguj"):
            if hmac.compare_digest(pwd, _app_password):
                st.session_state["authenticated"] = True
                st.session_state["login_attempts"] = 0
                st.rerun()
            else:
                st.session_state["login_attempts"] += 1
                if st.session_state["login_attempts"] >= 5:
                    st.session_state["lockout_until"] = time.time() + 300
                st.error("Nieprawidłowe hasło.")
        st.stop()

# ---------------------------------------------------------------------------
# Walidacja kluczy API
# ---------------------------------------------------------------------------

if not _get_secret("GEMINI_API_KEY"):
    st.error("Brak klucza GEMINI_API_KEY. Ustaw go w pliku .env lub Streamlit Secrets.")
    st.stop()

# ---------------------------------------------------------------------------
# Inicjalizacja limitera API
# ---------------------------------------------------------------------------

if "api_calls_count" not in st.session_state:
    st.session_state["api_calls_count"] = 0

# ---------------------------------------------------------------------------
# Naglowek
# ---------------------------------------------------------------------------

st.markdown("""
<div class="gz-header">
    <div class="gz-badge">
        <div class="gz-badge-dot"></div>
        <span style="font-size:12px;font-weight:600;color:#a8893e;letter-spacing:0.5px;">GranitoweZlewy</span>
    </div>
    <h1>Generator <span>Aukcji</span> Produktowych</h1>
    <p>Grafiki AI · Opisy SEO · Allegro · Shoper · BaseLinker</p>
</div>
""", unsafe_allow_html=True)

# B7: Koszt API w info bar
MAX_API_CALLS_PER_SESSION = 30
MAX_REGEN_PER_SESSION = 10

api_count = st.session_state.get("api_calls_count", 0)
if api_count > 0:
    estimated_cost_pln = api_count * 4.05 * 0.25
    st.markdown(f'<div class="gz-cost-counter">Wywołania API: <b>{api_count}/{MAX_API_CALLS_PER_SESSION}</b> · Szacunkowy koszt: <b>~{estimated_cost_pln:.0f} zł</b></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Funkcje pomocnicze
# ---------------------------------------------------------------------------

ALLOWED_HTML_TAGS = {'h2', 'h3', 'p', 'ul', 'ol', 'li', 'b', 'strong', 'br', 'em', 'small'}

# Komunikaty bledow API po polsku
ERROR_MESSAGES_PL = {
    "429": "Zbyt wiele zapytań do API. Odczekaj minutę i spróbuj ponownie.",
    "500": "Błąd serwera Gemini. Spróbuj ponownie za chwilę.",
    "503": "Serwer Gemini tymczasowo niedostępny. Spróbuj za minutę.",
    "RESOURCE_EXHAUSTED": "Wyczerpano limit API. Odczekaj kilka minut.",
    "SAFETY": "Gemini zablokował treść (filtr bezpieczeństwa). Zmień specyfikację i spróbuj ponownie.",
    "RECITATION": "Gemini wykrył potencjalną duplikację treści. Zmień opis i spróbuj ponownie.",
    "DEADLINE_EXCEEDED": "Przekroczono czas oczekiwania (120s). Spróbuj z mniejszą liczbą zdjęć.",
}


def get_user_error(e):
    """Mapuje wyjątek API na komunikat PL."""
    error_str = str(e)
    for code, msg in ERROR_MESSAGES_PL.items():
        if code in error_str:
            return msg
    return f"Błąd API: {error_str[:150]}"


def sanitize_html(html_text):
    """Usuwa tagi HTML spoza whitelisty, event handlers i atrybuty (ochrona przed XSS)."""
    # Decode encji HTML przed filtrowaniem (bypass &#111;nclick → onclick)
    html_text = html_lib.unescape(html_text)
    # Usun event handlers (onclick, onload, onerror, etc.)
    html_text = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', html_text, flags=re.IGNORECASE)
    html_text = re.sub(r'\s+on\w+\s*=\s*\S+', '', html_text, flags=re.IGNORECASE)

    def replace_tag(match):
        full_tag = match.group(1)
        tag_name = full_tag.split()[0].strip('/').lower()
        if tag_name not in ALLOWED_HTML_TAGS:
            return ''
        if full_tag.startswith('/'):
            return f'</{tag_name}>'
        return f'<{tag_name}>'
    return re.sub(r'<(/?\w[^>]*)>', replace_tag, html_text)


def generate_image(client, prompt_text, images, task_name, progress_callback=None):
    """Generuje obraz przez Gemini API. Zwraca PIL Image lub None."""
    gen_config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(imageSize="2K"),
    )
    contents = [prompt_text] + images

    for attempt in range(1, 4):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=gen_config,
            )
            if not response.parts:
                return None
            if not response.candidates:
                return None
            for part in response.parts:
                if part.inline_data is not None and part.inline_data.data:
                    try:
                        img = PIL.Image.open(io.BytesIO(part.inline_data.data))
                        img.load()
                        return img
                    except Exception:
                        continue
            return None
        except Exception as e:
            error_str = str(e)
            if attempt < 3 and any(code in error_str for code in ["429", "500", "503", "RESOURCE_EXHAUSTED"]):
                time.sleep(10 * attempt)
            else:
                raise
    return None


def create_zip(images_dict, description_text, output_path):
    """Tworzy ZIP z grafikami i opisem produktu."""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, img in images_dict.items():
            tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            try:
                img.save(tmp.name)
                # A11: czytelne nazwy plikow
                if name.startswith("zdjecie_oryginalne_"):
                    zf.write(tmp.name, f"grafiki/oryginaly/{name}.png")
                else:
                    zf.write(tmp.name, f"grafiki/wygenerowane/{name}.png")
            finally:
                os.unlink(tmp.name)
        if description_text:
            zf.writestr("opis-produktu.html", description_text)
            zf.writestr("opis-produktu.txt", description_text)


def render_bl_push_section(sections, all_results, timestamp,
                            cena_brutto, stan_magazyn, ean_code,
                            waga_kg, wysokosc_cm, szerokosc_cm, dlugosc_cm,
                            catalog_name, kategoria, key_suffix=""):
    """Renderuje sekcje ZIP + BaseLinker push (deduplikacja)."""
    col_zip, col_bl = st.columns(2)

    with col_zip:
        zip_path = OUTPUT_DIR / f"aukcja_{timestamp}.zip"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        desc_text = sections.get("opis", "") or st.session_state.get("last_desc_raw", "")
        create_zip(all_results, desc_text, zip_path)
        # B4: rotacja ZIP-ow
        cleanup_old_outputs(OUTPUT_DIR, max_files=50)
        with open(zip_path, "rb") as zf:
            st.download_button(
                "Pobierz ZIP",
                data=zf.read(),
                file_name=f"aukcja_{timestamp}.zip",
                mime="application/zip",
                use_container_width=True,
                key=f"dl_zip_{key_suffix}",
            )

    with col_bl:
        bl_token = _get_secret("BASELINKER_TOKEN")
        if bl_token:
            product_name = sections.get("tytul") or f"Produkt {timestamp}"
            product_desc = sections.get("opis") or desc_text
            product_sku = sections.get("sku") or f"GZ-{timestamp}"

            # Walidacja przed pushem
            bl_warnings = []
            if cena_brutto == 0:
                bl_warnings.append("Cena = 0.00 zł")
            if not product_name or product_name.startswith("Produkt "):
                bl_warnings.append("Brak tytułu")
            if waga_kg == 0:
                bl_warnings.append("Waga = 0 kg")

            if bl_warnings:
                st.warning(f"Uwaga: {', '.join(bl_warnings)}. Dane trafią do BaseLinker.")

            # Podgląd danych
            with st.expander("Podgląd danych do wysłania", expanded=False):
                st.markdown(f"**Nazwa:** {product_name}")
                st.markdown(f"**SKU:** {product_sku}")
                st.markdown(f"**Cena:** {cena_brutto} zł · **Stan:** {stan_magazyn} szt.")
                st.markdown(f"**Waga:** {waga_kg} kg · **Wymiary:** {szerokosc_cm}x{dlugosc_cm}x{wysokosc_cm} cm")
                st.markdown(f"**Grafik:** {len(all_results)} · **Katalog:** {catalog_name}")

            # A5: BL confirm dialog (dwuetapowy)
            confirm_key = f"bl_confirm_{key_suffix}"
            if not st.session_state.get(confirm_key):
                # A4: type secondary
                if st.button("Wyślij do BaseLinker", use_container_width=True, type="secondary",
                             key=f"bl_push_{key_suffix}"):
                    st.session_state[confirm_key] = True
                    st.rerun()
            else:
                product_name_short = (sections.get("tytul") or "produkt")[:40]
                st.warning(f"Wysłać '{product_name_short}' do BaseLinker?")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("Tak, wyślij", key=f"bl_yes_{key_suffix}", type="primary"):
                        try:
                            inv_id = int(_get_secret("BASELINKER_INVENTORY_ID", "8075"))
                            pg_id = int(_get_secret("BASELINKER_PRICE_GROUP_ID", "3778"))
                            wh_id = _get_secret("BASELINKER_WAREHOUSE_ID", "bl_5255")

                            # B5: deduplikacja SKU
                            existing_id = check_sku_exists(bl_token, inv_id, product_sku)
                            if existing_id:
                                st.warning(f"Produkt z SKU '{product_sku}' już istnieje w BaseLinker (ID: {existing_id}). Nadpisuję.")

                            bl_result = send_to_baselinker(
                                token=bl_token,
                                inventory_id=inv_id,
                                price_group_id=pg_id,
                                warehouse_id=wh_id,
                                name=product_name,
                                description_html=product_desc,
                                images_dict=all_results,
                                price=cena_brutto,
                                sku=product_sku,
                                stock=stan_magazyn,
                                ean=ean_code,
                                weight=waga_kg,
                                height=wysokosc_cm,
                                width=szerokosc_cm,
                                length=dlugosc_cm,
                                catalog_name=catalog_name,
                                kategoria=kategoria,
                            )
                            product_id = bl_result.get("product_id", "?")
                            st.success(f"Wysłano do BaseLinker (ID: {product_id})")
                        except Exception as e:
                            st.error(f"Błąd BaseLinker: {str(e)[:200]}")
                        st.session_state.pop(confirm_key, None)
                with col_no:
                    if st.button("Anuluj", key=f"bl_no_{key_suffix}"):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
        else:
            st.info("Ustaw BASELINKER_TOKEN w .env")


def render_description_chat():
    """Sekcja czatu do poprawek opisu aukcji."""
    sections = st.session_state.get("last_sections", {})
    desc_text = st.session_state.get("last_desc_raw", "")

    if not desc_text or not sections.get("opis"):
        return

    # Inicjalizacja
    if "description_revisions" not in st.session_state:
        st.session_state["description_revisions"] = []

    MAX_REVISIONS = 5
    current_count = len(st.session_state["description_revisions"])

    st.markdown("#### Popraw opis")

    if current_count >= MAX_REVISIONS:
        st.warning(f"Osiągnąłeś limit {MAX_REVISIONS} poprawek. Wygeneruj opis od nowa.")
        if st.session_state["description_revisions"]:
            with st.expander(f"Historia poprawek ({current_count})"):
                for i, rev in enumerate(st.session_state["description_revisions"], 1):
                    st.markdown(f"**{i}.** {rev['instruction']}  \n`{rev['timestamp']}`")
        return

    col_input, col_actions = st.columns([3, 1])
    with col_input:
        revision_instruction = st.text_area(
            "Co zmienić w opisie?",
            placeholder="np. Zmień nagłówek na bardziej sprzedażowy, Dodaj informację o gwarancji 5 lat, Skróć opis o połowę",
            key="revision_instruction",
            height=80,
        )
    with col_actions:
        st.caption(f"Poprawka {current_count + 1}/{MAX_REVISIONS}")
        is_processing = st.session_state.get("revision_processing", False)
        revise_btn = st.button(
            "Popraw opis",
            key="revise_desc_btn",
            use_container_width=True,
            disabled=is_processing,
        )
        if current_count > 0:
            undo_btn = st.button("Cofnij ostatnią", key="undo_revision_btn", use_container_width=True)
        else:
            undo_btn = False

    # Historia poprawek
    if st.session_state["description_revisions"]:
        with st.expander(f"Historia poprawek ({current_count})"):
            for i, rev in enumerate(st.session_state["description_revisions"], 1):
                st.markdown(f"**{i}.** {rev['instruction']}  \n`{rev['timestamp']}`")

    # Obsługa poprawki
    if revise_btn and revision_instruction.strip():
        _handle_revision(sections, revision_instruction)

    # Obsługa cofnięcia
    if undo_btn and st.session_state["description_revisions"]:
        last = st.session_state["description_revisions"].pop()
        st.session_state["last_sections"]["opis"] = last["previous_html"]
        st.session_state["last_desc_raw"] = last["previous_html"]
        st.rerun()


def _handle_revision(sections, revision_instruction):
    """Wysyła poprawkę opisu do Gemini i aktualizuje session_state."""
    current_html = sections.get("opis", "") or st.session_state.get("last_desc_raw", "")
    api_key = _get_secret("GEMINI_API_KEY")

    if not api_key:
        st.error("Brak klucza GEMINI_API_KEY.")
        return

    if st.session_state.get("api_calls_count", 0) >= MAX_API_CALLS_PER_SESSION:
        st.error(f"Osiągnąłeś limit {MAX_API_CALLS_PER_SESSION} wywołań API w tej sesji.")
        return

    st.session_state["revision_processing"] = True

    with st.spinner("Poprawiam opis..."):
        try:
            client = genai.Client(api_key=api_key)
            revision_prompt = get_description_revision_prompt(current_html, revision_instruction)

            response = client.models.generate_content(
                model=MODEL,
                contents=[revision_prompt],
                config=types.GenerateContentConfig(response_modalities=["TEXT"]),
            )

            st.session_state["api_calls_count"] = st.session_state.get("api_calls_count", 0) + 1

            if not response.parts:
                st.warning("AI nie wygenerowało odpowiedzi. Spróbuj ponownie.")
                st.session_state["revision_processing"] = False
                return

            new_desc = ""
            for part in response.parts:
                if part.text:
                    new_desc += part.text

            new_desc = new_desc.strip()

            # Walidacja: czy Gemini zwrócił HTML
            if "<h2" not in new_desc.lower() and "<p" not in new_desc.lower():
                st.warning("AI nie zwróciło poprawnego HTML. Spróbuj inaczej sformułować polecenie.")
                st.session_state["revision_processing"] = False
                return

            # Sanityzacja XSS
            new_desc = sanitize_html(new_desc)

            # Zapisz poprzednią wersję
            st.session_state["description_revisions"].append({
                "instruction": revision_instruction,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "previous_html": current_html,
            })

            # Aktualizuj opis w session_state
            st.session_state["last_sections"]["opis"] = new_desc
            st.session_state["last_desc_raw"] = new_desc

            # Sprawdź ban listę
            found_banned = check_ban_list(new_desc)
            if found_banned:
                st.warning(f"Znaleziono {len(found_banned)} fraz z ban listy w poprawionym opisie: {', '.join(found_banned[:5])}")

            st.session_state["revision_processing"] = False
            st.rerun()

        except Exception as e:
            st.error(f"Poprawka opisu: {get_user_error(e)}")
        finally:
            st.session_state["revision_processing"] = False


def validate_allegro_title(title):
    """Waliduje tytuł Allegro. Zwraca listę {status: 'ok'|'warn'|'error', text: str}."""
    checks = []
    length = len(title)
    if 60 <= length <= 75:
        checks.append({"status": "ok", "text": f"{length}/75 zn."})
    elif length < 60:
        checks.append({"status": "warn", "text": f"{length}/75 zn. (za krótki)"})
    else:
        checks.append({"status": "error", "text": f"{length}/75 zn. (za długi)"})

    # CAPS CHECK
    words = title.split()
    caps_words = [w for w in words if len(w) > 3 and w.isupper()]
    if caps_words:
        checks.append({"status": "error", "text": f"CAPS: {', '.join(caps_words)}"})

    # Zakazane
    banned = ["tanio", "okazja", "nowość", "promocja", "hit"]
    found = [b for b in banned if b.lower() in title.lower()]
    if found:
        checks.append({"status": "error", "text": f"Zakazane: {', '.join(found)}"})
    else:
        checks.append({"status": "ok", "text": "Brak zakazanych"})

    return checks


def render_results_section(all_results, sections, desc_text):
    """Renderuje sekcje wynikow (grafiki + opis + parametry)."""
    st.markdown(f"""
    <div class="gz-results">
        <div class="gz-results-header">
            <h3>Wyniki generowania</h3>
            <span class="gz-results-badge">{len(all_results)} grafik · opis · parametry</span>
        </div>
    </div>""", unsafe_allow_html=True)

    if all_results:
        st.markdown("#### Grafiki produktowe")
        img_cols = st.columns(min(len(all_results), 3))
        for i, (name, img) in enumerate(all_results.items()):
            with img_cols[i % 3]:
                label = name.rsplit("_", 1)[0].replace("-", " ").replace("_", " ")
                st.image(img, caption=label, use_container_width=True)

    if desc_text:
        st.markdown("#### Opis aukcji Allegro")
        tytul = sections.get("tytul", "")
        if tytul:
            st.markdown('**Tytuł Allegro** (kliknij ikonę aby skopiować)')
            st.code(tytul)

            # Badges walidacji
            checks = validate_allegro_title(tytul)
            badges_html = ' '.join(
                f'<span class="gz-badge-{c["status"]}">{c["text"]}</span>'
                for c in checks
            )
            st.markdown(f'<div style="margin-bottom:12px;">{badges_html}</div>', unsafe_allow_html=True)

        if sections.get("opis"):
            tab_preview, tab_code = st.tabs(["Podgląd", "Kod HTML"])
            with tab_preview:
                safe_opis = sanitize_html(sections["opis"])
                allegro_wrapper = f'''<div style="font-family: Arial, sans-serif; max-width: 800px; padding: 20px; background: #fff; line-height: 1.6;">
{safe_opis}
</div>'''
                st.components.v1.html(allegro_wrapper, height=600, scrolling=True)
            with tab_code:
                st.markdown("Kliknij ikonę kopiowania w prawym górnym rogu bloku kodu:")
                st.code(sections["opis"], language="html")

        if sections.get("parametry_dict"):
            with st.expander("Parametry techniczne (JSON)"):
                st.json(sections["parametry_dict"])
        if sections.get("bullets"):
            with st.expander("Bullet Points"):
                st.markdown(sections["bullets"])
        if sections.get("sku"):
            st.markdown(f'**SKU:** `{sections["sku"]}`')

    # Licznik kosztów API
    if all_results:
        images_count = len(all_results)
        image_cost_usd = images_count * 0.134
        desc_cost_usd = 0.05
        total_usd = image_cost_usd + desc_cost_usd
        total_pln = total_usd * 4.05
        st.markdown(f'''<div class="gz-cost-counter">
Koszt API: {images_count} grafik x $0.134 + opis x $0.05 = <b>${total_usd:.2f}</b> (~{total_pln:.2f} zł)
</div>''', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# A3: Historia generowań (expander zamiast sidebar)
# ---------------------------------------------------------------------------

# (przesunieta do main area, PO formularzu, PRZED wynikami - patrz nizej)

# ---------------------------------------------------------------------------
# A1: Formularz (sekwencyjny layout zamiast dwukolumnowego)
# ---------------------------------------------------------------------------

# --- SEKCJA: FORMULARZ ---
st.markdown("### Dane produktu")

# Wybor katalogu
catalog_names = get_catalog_display_names()
catalog_key = st.selectbox(
    "Katalog produktowy",
    list(catalog_names.keys()),
    format_func=lambda k: catalog_names[k],
    index=0,
)

# Wyczyść wyniki przy zmianie katalogu
if st.session_state.get("last_catalog") and st.session_state["last_catalog"] != catalog_key:
    for k in ["last_results", "last_sections", "last_desc_raw", "last_timestamp",
               "last_extraction", "source_images", "last_kolory",
               "auto_waga_kg", "auto_wysokosc_cm", "auto_szerokosc_cm", "auto_dlugosc_cm",
               "description_revisions", "regen_count"]:
        st.session_state.pop(k, None)

# Kategorie z wybranego katalogu (Z3: + "Inna")
kategorie_list = get_categories(catalog_key)
kategorie_z_inna = kategorie_list + ["Inna (wpisz ręcznie)"]
kategoria = st.selectbox("Kategoria", kategorie_z_inna, index=0)
if kategoria == "Inna (wpisz ręcznie)":
    kategoria = st.text_input("Nazwa kategorii", placeholder="np. Kran ogrodowy")

# Kolory (Z2: osobne per element dla Granitowe Zlewy)
kat = kategoria.lower() if kategoria else ""
if catalog_key == "granitowe_zlewy":
    kolory_pe = get_kolory_per_element(catalog_key)
    col_k1, col_k2 = st.columns(2)
    kolor_zlew = "Czarny nakrapiany"
    kolor_bateria = "Czarno-złota"
    kolor_syfon = "Złoty"
    kolor_dozownik = "Złoty"

    if "zlew" in kat:
        with col_k1:
            kolor_zlew = st.selectbox("Kolor zlewu", list(kolory_pe["kolor_zlew"].keys()))
    if "bateria" in kat:
        with col_k2:
            kolor_bateria = st.selectbox("Kolor baterii", list(kolory_pe["kolor_bateria"].keys()))
    if "syfon" in kat:
        with col_k1:
            kolor_syfon = st.selectbox("Kolor syfonu (widoczna część)", list(kolory_pe["kolor_syfon_widoczny"].keys()))
    if "dozownik" in kat:
        with col_k2:
            kolor_dozownik = st.selectbox("Kolor dozownika", list(kolory_pe["kolor_dozownik"].keys()))
    kolor_akcent = kolor_zlew  # backward compat
else:
    # LED i inne: stary selectbox
    kolor_map = get_kolor_map(catalog_key)
    kolor_akcent = st.selectbox(
        "Kolor akcentów",
        list(kolor_map.keys()),
        index=0,
    )
    kolor_zlew = kolor_bateria = kolor_syfon = kolor_dozownik = ""

uploaded_files = st.file_uploader(
    "Zdjęcia produktu (JPG/PNG, do 10 plików)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

if uploaded_files:
    st.markdown(f'<span class="gz-tag gz-tag--success">{len(uploaded_files)} zdjęć wgranych</span>', unsafe_allow_html=True)
    # A2: Thumbnails max 3 kolumny
    thumb_cols = st.columns(min(len(uploaded_files), 3))
    for i, f in enumerate(uploaded_files[:3]):
        with thumb_cols[i]:
            st.image(f, use_container_width=True)
    if len(uploaded_files) > 3:
        st.caption(f"+ {len(uploaded_files) - 3} kolejnych zdjęć")

specyfikacja = st.text_area(
    "Specyfikacja produktu",
    height=200,
    placeholder="Wklej specyfikację z karty producenta...\n\nNp.:\nTyp: nablatowy\nKolor: czarny nakrapiany\nWymiary: 500x790mm\nGłębokość komory: 185mm\nMateriał: 80% granit, 20% żywica\nSyfon: w zestawie (chrom)",
)

# A8: EAN label czytelniejszy
ean_code = st.text_input("Kod EAN", placeholder="np. 5904123456789 (13 cyfr, opcjonalne)",
                         help="Znajdziesz na etykiecie produktu lub w dokumentach dostawcy.")

col_price, col_stock = st.columns(2)
with col_price:
    cena_brutto = st.number_input("Cena brutto (zł)", min_value=0.0, value=0.0, step=10.0)
with col_stock:
    stan_magazyn = st.number_input("Stan magazynowy", min_value=0, value=1, step=1)

# Z4: Wymiary w expander (auto-uzupełniane ze specyfikacji)
with st.expander("Wymiary i waga (uzupełniane automatycznie)", expanded=False):
    st.caption("Pola uzupełniane automatycznie ze specyfikacji. Nadpisz ręcznie jeśli potrzeba.")
    col_w, col_h = st.columns(2)
    with col_w:
        waga_kg = st.number_input("Waga (kg)", min_value=0.0,
                                  value=st.session_state.get("auto_waga_kg", 0.0), step=0.5)
    with col_h:
        wysokosc_cm = st.number_input("Wysokość (cm)", min_value=0.0,
                                      value=st.session_state.get("auto_wysokosc_cm", 0.0), step=1.0)
    col_wd, col_ln = st.columns(2)
    with col_wd:
        szerokosc_cm = st.number_input("Szerokość (cm)", min_value=0.0,
                                       value=st.session_state.get("auto_szerokosc_cm", 0.0), step=1.0)
    with col_ln:
        dlugosc_cm = st.number_input("Długość (cm)", min_value=0.0,
                                     value=st.session_state.get("auto_dlugosc_cm", 0.0), step=1.0)

generate_btn = st.button("Generuj aukcję", use_container_width=True, type="primary")

# A14: separator stylowany
st.markdown('<hr class="gz-separator">', unsafe_allow_html=True)

# A3: Historia generowań (expander w main area)
history = load_history()
if history:
    with st.expander(f"Historia generowań ({len(history)})"):
        for entry in history[:10]:
            ts = entry.get("timestamp", "")
            title = entry.get("title", "Bez tytułu")[:35]
            sku = entry.get("sku", "")
            catalog = entry.get("catalog", "")
            bl_id = entry.get("bl_product_id")
            status = "BL" if bl_id else "Lokalne"
            st.markdown(f"**{title}**  \n`{sku}` · {catalog} · {status} · {ts}")

# A14: separator stylowany
st.markdown('<hr class="gz-separator">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# A1: SEKCJA WYNIKI (sekwencyjnie pod formularzem)
# ---------------------------------------------------------------------------

if generate_btn:
    # --- Pre-flight walidacja ---
    preflight_ok = True

    if not uploaded_files:
        st.error("Wgraj co najmniej 1 zdjęcie produktu.")
        preflight_ok = False
    else:
        if len(uploaded_files) > 10:
            st.error(f"Za dużo plików ({len(uploaded_files)}). Maksimum: 10.")
            preflight_ok = False
        for uf in uploaded_files:
            if uf.size > 10 * 1024 * 1024:
                st.error(f"Plik '{uf.name}' jest za duży ({uf.size // (1024*1024)} MB). Maksymalny rozmiar: 10 MB.")
                preflight_ok = False
                break

    if not specyfikacja.strip():
        st.error("Wklej specyfikację produktu.")
        preflight_ok = False
    elif len(specyfikacja.strip()) < 50:
        st.warning("Krótka specyfikacja (< 50 znaków). Im więcej danych, tym lepsze wyniki.")

    if len(specyfikacja) > 5000:
        st.error(f"Specyfikacja za długa ({len(specyfikacja)} zn.). Maksimum: 5000 znaków.")
        preflight_ok = False

    if ean_code and not re.match(r'^\d{8,13}$', ean_code):
        st.warning("Kod EAN powinien zawierać 8-13 cyfr. Sprawdź poprawność.")

    if st.session_state["api_calls_count"] >= MAX_API_CALLS_PER_SESSION:
        st.error(f"Osiągnąłeś limit {MAX_API_CALLS_PER_SESSION} generowań w tej sesji.")
        preflight_ok = False

    if not preflight_ok:
        pass
    elif not GENAI_AVAILABLE:
        st.error("Brak SDK google-genai. Zainstaluj: pip install google-genai")
    else:
            api_key = _get_secret("GEMINI_API_KEY")
            client = genai.Client(api_key=api_key)
            st.session_state["api_calls_count"] += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # B3: try/except per plik PIL
            pil_images = []
            for f in uploaded_files:
                try:
                    img_bytes = f.getvalue()
                    buf = io.BytesIO(img_bytes)
                    img = PIL.Image.open(buf)
                    img.load()
                    pil_images.append(img)
                except Exception:
                    st.warning(f"Plik '{f.name}' jest uszkodzony lub nieobsługiwany. Pominięto.")

            if not pil_images:
                st.error("Żadne zdjęcie nie zostało wczytane. Sprawdź pliki i spróbuj ponownie.")
                st.stop()

            # Auto-ekstrakcja danych ze specyfikacji
            with st.spinner("Analizuję specyfikację..."):
                extracted = extract_spec_data(client, specyfikacja, pil_images)

                # Auto-uzupełnij pola jeśli puste
                if extracted.get("waga_kg") and waga_kg == 0:
                    waga_kg = extracted["waga_kg"]
                    st.session_state["auto_waga_kg"] = waga_kg
                if extracted.get("wysokosc_cm") and wysokosc_cm == 0:
                    wysokosc_cm = extracted["wysokosc_cm"]
                    st.session_state["auto_wysokosc_cm"] = wysokosc_cm
                if extracted.get("szerokosc_cm") and szerokosc_cm == 0:
                    szerokosc_cm = extracted["szerokosc_cm"]
                    st.session_state["auto_szerokosc_cm"] = szerokosc_cm
                if extracted.get("dlugosc_cm") and dlugosc_cm == 0:
                    dlugosc_cm = extracted["dlugosc_cm"]
                    st.session_state["auto_dlugosc_cm"] = dlugosc_cm

                # Auto-kategoria
                if extracted.get("kategoria_sugerowana"):
                    st.session_state["suggested_category"] = extracted["kategoria_sugerowana"]

                st.session_state["last_extraction"] = extracted

                # Z4: Inline feedback z wymiarów i wagi
                dims_info = []
                if extracted.get("waga_kg"):
                    dims_info.append(f"waga {extracted['waga_kg']} kg")
                if extracted.get("szerokosc_cm") and extracted.get("dlugosc_cm"):
                    h = extracted.get("wysokosc_cm", "?")
                    dims_info.append(f"wymiary {extracted['szerokosc_cm']}x{extracted['dlugosc_cm']}x{h} cm")
                if dims_info:
                    st.info(f"Wykryto: {', '.join(dims_info)}")

                # Inline feedback z ekstrakcji
                filled = {k: v for k, v in extracted.items() if v is not None}
                if filled:
                    fields_info = ", ".join(f"{k}: {v}" for k, v in list(filled.items())[:5])
                    st.success(f"Wykryto {len(filled)} pól ze specyfikacji: {fields_info}")
                else:
                    st.info("Nie udało się wyekstrahować danych. Uzupełnij ręcznie.")

            if catalog_key == "granitowe_zlewy":
                prompts_zestawy, prompts_lifestyle = get_image_prompts(
                    kategoria, kolor_zlew=kolor_zlew, kolor_bateria=kolor_bateria,
                    kolor_syfon=kolor_syfon, kolor_dozownik=kolor_dozownik,
                    catalog_name=catalog_key
                )
            else:
                prompts_zestawy, prompts_lifestyle = get_image_prompts(
                    kategoria, kolor_zlew=kolor_akcent, catalog_name=catalog_key
                )

            all_results = {}
            total_tasks = len(prompts_zestawy) + len(prompts_lifestyle) + 1
            progress = st.progress(0, text="Startuję generowanie...")
            # A12: status_msg placeholder
            status_msg = st.empty()

            imgs_for_set = pil_images[:4] if len(pil_images) >= 2 else pil_images

            st.session_state["source_images"] = pil_images
            st.session_state["last_kategoria"] = kategoria
            st.session_state["last_kolory"] = {
                "kolor_zlew": kolor_zlew,
                "kolor_bateria": kolor_bateria,
                "kolor_syfon": kolor_syfon,
                "kolor_dozownik": kolor_dozownik,
            }
            st.session_state["last_catalog"] = catalog_key

            # Wyczyść poprawki z poprzedniego generowania
            st.session_state.pop("description_revisions", None)

            # --- Packshoty ---
            for i, prompt_cfg in enumerate(prompts_zestawy):
                step = i + 1
                # A12: jawny komunikat w status_msg
                status_msg.info(f"Krok {step}/{total_tasks}: {prompt_cfg['name']}")
                progress.progress(step / total_tasks)
                try:
                    result = generate_image(client, prompt_cfg["prompt"], imgs_for_set, prompt_cfg["name"])
                    if result:
                        key = f"packshot_{i+1}_{timestamp}"
                        all_results[key] = result
                except Exception as e:
                    st.warning(f"{prompt_cfg['name']}: {get_user_error(e)}")

            # --- Lifestyle ---
            for i, prompt_cfg in enumerate(prompts_lifestyle):
                step = len(prompts_zestawy) + i + 1
                # A12: jawny komunikat w status_msg
                status_msg.info(f"Krok {step}/{total_tasks}: {prompt_cfg['name']}")
                progress.progress(step / total_tasks)
                try:
                    result = generate_image(client, prompt_cfg["prompt"], imgs_for_set, prompt_cfg["name"])
                    if result:
                        key = f"lifestyle_{i+1}_{timestamp}"
                        all_results[key] = result
                except Exception as e:
                    st.warning(f"{prompt_cfg['name']}: {get_user_error(e)}")

            status_msg.info(f"Krok {total_tasks}/{total_tasks}: Generowanie opisu Allegro...")
            progress.progress((total_tasks - 1) / total_tasks)

            # --- Opis B2C ---
            desc_text = ""
            try:
                desc_prompt = generate_description_prompt(
                    specyfikacja, kategoria, catalog_key,
                    kolor_zlew=kolor_zlew, kolor_bateria=kolor_bateria,
                    kolor_syfon=kolor_syfon, kolor_dozownik=kolor_dozownik,
                )
                desc_response = client.models.generate_content(
                    model=MODEL,
                    contents=[desc_prompt] + pil_images[:4],
                    config=types.GenerateContentConfig(
                        response_modalities=["TEXT"],
                    ),
                )
                if not desc_response.candidates:
                    st.warning("Opis zablokowany przez filtr bezpieczeństwa. Spróbuj ponownie.")
                elif desc_response.parts:
                    for part in desc_response.parts:
                        if part.text:
                            desc_text += part.text
            except Exception as e:
                st.warning(f"Opis: {get_user_error(e)}")

            # A12: wyczyszczenie progress i status
            status_msg.empty()
            progress.empty()

            # --- Parsuj sekcje ---
            sections = parse_description_sections(desc_text)

            # B1: Walidacja ban listy na pierwszym generowaniu
            if desc_text:
                found_banned = check_ban_list(desc_text)
                if found_banned:
                    st.warning(f"Opis zawiera {len(found_banned)} fraz z ban listy: {', '.join(found_banned[:5])}. Użyj czatu do poprawek.")

            # Zmien nazwy grafik na bazujace na tytule Allegro
            if sections["tytul"]:
                slug = re.sub(r'[^\w\s-]', '', sections["tytul"][:50]).strip().replace(' ', '-')
                renamed = {}
                for key, img in all_results.items():
                    prefix = key.rsplit("_", 1)[0]
                    renamed[f"{slug}_{prefix}"] = img
                all_results = renamed

            # A11: czytelne nazwy plikow oryginalnych
            for i, img in enumerate(pil_images):
                all_results[f"zdjecie_oryginalne_{i+1}"] = img

            # Zapisz w session_state
            st.session_state["last_results"] = all_results
            st.session_state["last_sections"] = sections
            st.session_state["last_desc_raw"] = desc_text
            st.session_state["last_timestamp"] = timestamp

            # Zapisz do historii
            save_generation(
                title=sections.get("tytul", ""),
                sku=sections.get("sku", ""),
                catalog=catalog_key,
                kategoria=kategoria,
                timestamp=timestamp,
                images_count=len(all_results),
            )

            # --- Wyniki ---
            render_results_section(all_results, sections, desc_text)

            # A13: disclaimer o weryfikacji opisow
            st.caption("Sprawdź wygenerowany opis przed publikacją. AI może zawierać nieścisłości w wymiarach lub parametrach.")

            # Czat do poprawek opisu
            render_description_chat()

            # A10: usunięto zduplikowany expander JSON (inline feedback wystarczy)

            # --- Akcje ---
            if all_results or desc_text:
                st.markdown('<hr class="gz-separator">', unsafe_allow_html=True)
                render_bl_push_section(
                    sections, all_results, timestamp,
                    cena_brutto, stan_magazyn, ean_code,
                    waga_kg, wysokosc_cm, szerokosc_cm, dlugosc_cm,
                    catalog_key, kategoria, key_suffix="gen",
                )

else:
    # Pokaz wyniki z session_state
    if "last_results" in st.session_state and st.session_state["last_results"]:
        all_results = st.session_state["last_results"]
        sections = st.session_state.get("last_sections", {})
        desc_text = st.session_state.get("last_desc_raw", "")
        timestamp = st.session_state.get("last_timestamp", "")
        last_catalog = st.session_state.get("last_catalog", catalog_key)
        last_kategoria = st.session_state.get("last_kategoria", kategoria)

        render_results_section(all_results, sections, desc_text)

        # A13: disclaimer o weryfikacji opisow
        st.caption("Sprawdź wygenerowany opis przed publikacją. AI może zawierać nieścisłości w wymiarach lub parametrach.")

        # Czat do poprawek opisu
        render_description_chat()

        # --- Regeneracja grafik ---
        if "source_images" in st.session_state and GENAI_AVAILABLE:
            st.markdown('<hr class="gz-separator">', unsafe_allow_html=True)
            st.markdown("#### Popraw grafikę")

            # B2: Limit regeneracji grafik
            regen_count = st.session_state.get("regen_count", 0)
            if regen_count >= MAX_REGEN_PER_SESSION:
                st.warning(f"Osiągnąłeś limit {MAX_REGEN_PER_SESSION} regeneracji grafik w tej sesji.")
            else:
                regen_mode = st.radio(
                    "Tryb regeneracji",
                    ["Drobna poprawka", "Wygeneruj od nowa"],
                    horizontal=True,
                    key="regen_mode",
                )

                img_keys = list(all_results.keys())
                img_labels = [k.rsplit("_", 1)[0].replace("-", " ").replace("_", " ") for k in img_keys]

                selected_idx = st.selectbox(
                    "Którą grafikę poprawić?",
                    range(len(img_keys)),
                    format_func=lambda i: img_labels[i],
                    key="regen_select",
                )

                is_edit = regen_mode == "Drobna poprawka"
                placeholder_text = (
                    "np. Zmień kolor baterii na srebrny, usuń naczynie w tle"
                    if is_edit
                    else "np. Inna kuchnia, skandynawska, jasna, z drewnianym blatem"
                )
                regen_instruction = st.text_area(
                    "Co zmienić?",
                    placeholder=placeholder_text,
                    key="regen_prompt",
                )

                if st.button("Regeneruj grafikę", key="regen_btn"):
                    if regen_instruction.strip():
                        api_key = _get_secret("GEMINI_API_KEY")
                        if api_key:
                            regen_client = genai.Client(api_key=api_key)
                            source_imgs = st.session_state["source_images"][:2]
                            current_img = all_results[img_keys[selected_idx]]

                            mode_key = "edit" if is_edit else "full"

                            if REGEN_AVAILABLE:
                                full_prompt = get_regen_prompt(mode_key, regen_instruction)
                            else:
                                if is_edit:
                                    full_prompt = (
                                        f"Modify this product image based on this instruction: {regen_instruction}. "
                                        f"Keep professional product photography quality. High resolution. "
                                        f"Do NOT add any text, labels, watermarks, or annotations."
                                    )
                                else:
                                    full_prompt = (
                                        f"Generate a new product lifestyle image based on this instruction: {regen_instruction}. "
                                        f"Use the product from the source photos. Professional photography quality. High resolution. "
                                        f"Do NOT add any text, labels, watermarks, or annotations."
                                    )

                            if is_edit:
                                regen_images = [current_img]
                            else:
                                regen_images = source_imgs

                            with st.spinner("Regeneruję grafikę..."):
                                try:
                                    new_img = generate_image(
                                        regen_client, full_prompt,
                                        regen_images,
                                        "Regeneracja",
                                    )
                                    if new_img:
                                        all_results[img_keys[selected_idx]] = new_img
                                        st.session_state["last_results"] = all_results
                                        # B2: inkrementacja licznika regeneracji
                                        st.session_state["regen_count"] = st.session_state.get("regen_count", 0) + 1
                                        st.session_state["api_calls_count"] = st.session_state.get("api_calls_count", 0) + 1
                                        st.rerun()
                                    else:
                                        st.warning("Nie udało się wygenerować nowej grafiki. Spróbuj inny opis.")
                                except Exception as e:
                                    st.error(f"Regeneracja: {get_user_error(e)}")
                    else:
                        st.warning("Opisz co chcesz zmienić w grafice.")

        # --- Akcje ---
        st.markdown('<hr class="gz-separator">', unsafe_allow_html=True)
        render_bl_push_section(
            sections, all_results, timestamp,
            cena_brutto, stan_magazyn, ean_code,
            waga_kg, wysokosc_cm, szerokosc_cm, dlugosc_cm,
            last_catalog, last_kategoria, key_suffix="cache",
        )

    else:
        # A6: Empty state visual
        st.markdown("""
        <div style="text-align:center;padding:60px 24px;color:#999;">
            <div style="font-size:56px;margin-bottom:20px;">◆</div>
            <p style="font-size:16px;font-weight:600;color:#1d1d1f;margin-bottom:8px;">Gotowy do generowania</p>
            <p style="font-size:14px;color:#6e6e73;max-width:400px;margin:0 auto;line-height:1.6;">
                Wypełnij dane produktu w formularzu powyżej i kliknij Generuj aukcję.<br>
                AI stworzy kompletną aukcję w ~2-3 minuty.
            </p>
        </div>
        """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Stopka
# ---------------------------------------------------------------------------

st.markdown("""
<div class="gz-footer">
    <p>Generator Aukcji v3.2 · GranitoweZlewy · powered by <span>nanoAI</span></p>
</div>
""", unsafe_allow_html=True)
