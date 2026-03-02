"""
Chat UI do edycji grafik i opisów aukcji.

render_image_chat: chat pod grafiką do edycji instrukcjami naturalnymi.
render_desc_chat: chat pod opisem Allegro do edycji instrukcjami.
"""

import html as html_lib
import io
import time
from datetime import datetime

import streamlit as st

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

from config import get_secret as _get_secret, MODEL
from prompts import get_regen_prompt, get_description_revision_prompt, check_ban_list


# ---------------------------------------------------------------------------
# Stałe
# ---------------------------------------------------------------------------

MAX_API_CALLS_PER_SESSION = 30
MAX_CHAT_MESSAGES = 10


def _check_api_limit() -> bool:
    """Sprawdza czy nie przekroczono limitu API. Zwraca True jeśli OK."""
    if st.session_state.get("api_calls_count", 0) >= MAX_API_CALLS_PER_SESSION:
        st.error(f"Limit {MAX_API_CALLS_PER_SESSION} wywołań API w tej sesji.")
        return False
    return True


def _get_client():
    """Zwraca klienta Gemini lub None."""
    api_key = _get_secret("GEMINI_API_KEY")
    if not api_key or not GENAI_AVAILABLE:
        return None
    return genai.Client(api_key=api_key)


# ---------------------------------------------------------------------------
# Chat do edycji grafik
# ---------------------------------------------------------------------------

def render_image_chat(image_key: str, current_prompt: str, all_results: dict, timestamp: str):
    """Renderuje chat pod grafiką do edycji instrukcjami naturalnymi.

    Args:
        image_key: klucz grafiki w all_results
        current_prompt: prompt użyty do wygenerowania grafiki
        all_results: dict z wszystkimi wynikami (PIL.Image)
        timestamp: timestamp generowania
    """
    if image_key not in all_results:
        return

    # Pomijaj oryginały
    if image_key.startswith("zdjecie_oryginalne_"):
        return

    chat_key = f"chat_history_{image_key}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    history = st.session_state[chat_key]

    with st.expander("Edytuj tę grafikę", expanded=False):
        # Historia zmian
        if history:
            for msg in history:
                role = msg.get("role", "user")
                text = msg.get("text", "")
                if role == "user":
                    st.markdown(f"**Ty:** {html_lib.escape(text)}")
                else:
                    st.markdown(f"**System:** {text}")

        if len(history) >= MAX_CHAT_MESSAGES * 2:
            st.info(f"Limit {MAX_CHAT_MESSAGES} edycji tej grafiki.")
            return

        col_input, col_btn = st.columns([3, 1])
        with col_input:
            instruction = st.text_input(
                "Instrukcja",
                placeholder="np. 'zmień kolor baterii na złoty'",
                key=f"img_chat_input_{image_key}",
                label_visibility="collapsed",
            )
        with col_btn:
            send = st.button("Wyślij", key=f"img_chat_send_{image_key}", use_container_width=True)

        if send and instruction.strip():
            if not _check_api_limit():
                return

            client = _get_client()
            if not client:
                st.error("Brak klucza API lub SDK google-genai.")
                return

            # Dodaj wiadomość użytkownika
            history.append({"role": "user", "text": instruction.strip(), "ts": datetime.now().isoformat()})

            with st.spinner("Edytuję grafikę..."):
                try:
                    edit_prompt = get_regen_prompt("edit", instruction.strip())
                    current_img = all_results[image_key]

                    gen_config = types.GenerateContentConfig(
                        response_modalities=["IMAGE", "TEXT"],
                        image_config=types.ImageConfig(imageSize="2K"),
                    )

                    # Dodaj zdjęcia źródłowe jeśli dostępne
                    images_input = [current_img]
                    source_imgs = st.session_state.get("source_images", [])
                    if source_imgs:
                        images_input = [current_img] + source_imgs[:2]

                    response = client.models.generate_content(
                        model=MODEL,
                        contents=[edit_prompt] + images_input,
                        config=gen_config,
                    )

                    st.session_state["api_calls_count"] = st.session_state.get("api_calls_count", 0) + 1
                    st.session_state["image_gen_count"] = st.session_state.get("image_gen_count", 0) + 1

                    new_img = None
                    if response.parts:
                        for part in response.parts:
                            if part.inline_data is not None and part.inline_data.data:
                                try:
                                    img = PIL.Image.open(io.BytesIO(part.inline_data.data))
                                    img.load()
                                    new_img = img
                                    break
                                except Exception:
                                    continue

                    if new_img:
                        all_results[image_key] = new_img
                        st.session_state["last_results"] = all_results
                        history.append({"role": "system", "text": "Gotowe. Zaktualizowałem grafikę.", "ts": datetime.now().isoformat()})
                        st.session_state[chat_key] = history
                        st.rerun()
                    else:
                        history.append({"role": "system", "text": "Nie udało się wygenerować. Spróbuj inaczej.", "ts": datetime.now().isoformat()})
                        st.session_state[chat_key] = history

                except Exception as e:
                    error_msg = str(e)[:150]
                    history.append({"role": "system", "text": f"Błąd: {error_msg}", "ts": datetime.now().isoformat()})
                    st.session_state[chat_key] = history
                    st.error(f"Błąd API: {error_msg}")


# ---------------------------------------------------------------------------
# Chat do edycji opisu
# ---------------------------------------------------------------------------

def render_desc_chat(desc_text: str, session_key: str = "desc_chat"):
    """Renderuje chat do edycji opisu Allegro.

    Args:
        desc_text: aktualny opis HTML
        session_key: klucz w session_state dla historii czatu
    """
    sections = st.session_state.get("last_sections", {})
    current_html = sections.get("opis", "") or desc_text

    if not current_html:
        return

    chat_key = f"{session_key}_history"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    # Inicjalizacja revisions (kompatybilność z istniejącym kodem)
    if "description_revisions" not in st.session_state:
        st.session_state["description_revisions"] = []

    history = st.session_state[chat_key]
    MAX_REVISIONS = 5
    current_count = len(st.session_state["description_revisions"])

    st.markdown("#### Popraw opis")

    # Edytowalny opis
    edited_desc = st.text_area(
        "Opis HTML (edytowalny)",
        value=current_html,
        height=300,
        key=f"{session_key}_editable",
    )

    # Zapisz ręczną edycję
    if edited_desc != current_html:
        col_save, col_reset = st.columns(2)
        with col_save:
            if st.button("Zapisz zmiany", key=f"{session_key}_save_manual"):
                st.session_state["description_revisions"].append({
                    "instruction": "(edycja ręczna)",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "previous_html": current_html,
                })
                st.session_state["last_sections"]["opis"] = edited_desc
                st.session_state["last_desc_raw"] = edited_desc
                st.rerun()
        with col_reset:
            if st.button("Cofnij zmiany", key=f"{session_key}_reset_manual"):
                st.rerun()

    if current_count >= MAX_REVISIONS:
        st.warning(f"Limit {MAX_REVISIONS} poprawek. Wygeneruj opis od nowa.")
        return

    # Chat AI
    col_input, col_actions = st.columns([3, 1])
    with col_input:
        instruction = st.text_input(
            "Instrukcja edycji",
            placeholder="np. 'skróć o 20%', 'dodaj emotikony', 'zmień nagłówek'",
            key=f"{session_key}_instruction",
        )
    with col_actions:
        st.caption(f"Poprawka {current_count + 1}/{MAX_REVISIONS}")
        revise_btn = st.button("Popraw opis", key=f"{session_key}_revise", use_container_width=True)
        if current_count > 0:
            undo_btn = st.button("Cofnij ostatnią", key=f"{session_key}_undo", use_container_width=True)
        else:
            undo_btn = False

    # Historia czatu
    if history:
        with st.expander(f"Historia poprawek ({len(history)})"):
            for msg in history:
                role = msg.get("role", "user")
                text = msg.get("text", "")
                if role == "user":
                    st.markdown(f"**Ty:** {html_lib.escape(text)}")
                else:
                    st.markdown(f"**AI:** {text}")

    # Obsługa poprawki AI
    if revise_btn and instruction.strip():
        if not _check_api_limit():
            return

        client = _get_client()
        if not client:
            st.error("Brak klucza API lub SDK google-genai.")
            return

        # Użyj aktualnego opisu (może być ręcznie edytowany)
        active_html = edited_desc if edited_desc else current_html

        history.append({"role": "user", "text": instruction.strip()})

        with st.spinner("Poprawiam opis..."):
            try:
                revision_prompt = get_description_revision_prompt(active_html, instruction.strip())
                response = client.models.generate_content(
                    model=MODEL,
                    contents=[revision_prompt],
                    config=types.GenerateContentConfig(response_modalities=["TEXT"]),
                )
                st.session_state["api_calls_count"] = st.session_state.get("api_calls_count", 0) + 1
                st.session_state["text_gen_count"] = st.session_state.get("text_gen_count", 0) + 1

                if not response.parts:
                    history.append({"role": "system", "text": "AI nie wygenerowało odpowiedzi."})
                    st.session_state[chat_key] = history
                    return

                new_desc = ""
                for part in response.parts:
                    if part.text:
                        new_desc += part.text
                new_desc = new_desc.strip()

                if "<h2" not in new_desc.lower() and "<p" not in new_desc.lower():
                    history.append({"role": "system", "text": "AI nie zwróciło poprawnego HTML."})
                    st.session_state[chat_key] = history
                    return

                # Zapisz poprzednia wersje
                st.session_state["description_revisions"].append({
                    "instruction": instruction.strip(),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "previous_html": active_html,
                })

                st.session_state["last_sections"]["opis"] = new_desc
                st.session_state["last_desc_raw"] = new_desc

                # Ban lista
                found_banned = check_ban_list(new_desc)
                status_msg = "Gotowe. Opis zaktualizowany."
                if found_banned:
                    status_msg += f" Uwaga: {len(found_banned)} fraz z ban listy."

                history.append({"role": "system", "text": status_msg})
                st.session_state[chat_key] = history
                st.rerun()

            except Exception as e:
                error_msg = str(e)[:150]
                history.append({"role": "system", "text": f"Błąd: {error_msg}"})
                st.session_state[chat_key] = history
                st.error(f"Błąd API: {error_msg}")

    # Cofniecie
    if undo_btn and st.session_state["description_revisions"]:
        last = st.session_state["description_revisions"].pop()
        st.session_state["last_sections"]["opis"] = last["previous_html"]
        st.session_state["last_desc_raw"] = last["previous_html"]
        if history:
            # Usuń ostatnią parę user+system
            while history and history[-1].get("role") == "system":
                history.pop()
            if history and history[-1].get("role") == "user":
                history.pop()
            st.session_state[chat_key] = history
        st.rerun()
