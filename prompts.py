"""
Prompty do generowania grafik i opisow produktowych.

Obsluguje rozne katalogi przez import z catalogs.py.
"""

import json
import re
from catalogs import get_kolor_map, get_kolory_per_element, get_seo_data, get_seo_key


# ---------------------------------------------------------------------------
# BAN LISTA anty-AI dla e-commerce / Allegro
# ---------------------------------------------------------------------------

BAN_LIST_ECOMMERCE: list[str] = [
    # --- Z BAN-LIST.md: Otwierające ---
    "zagłębmy się w",
    "w dzisiejszym dynamicznym świecie",
    "w erze cyfrowej transformacji",
    "jak zapewne wiesz",
    "nie jest tajemnicą, że",
    "wyobraź sobie świat, w którym",
    # --- Obiecujące ---
    "uwolnij swój potencjał",
    "przełomowe rozwiązanie",
    "rewolucyjne podejście",
    "wykorzystaj moc",
    "odkryj sekrety",
    "wznieś się na wyżyny",
    "osiągnij sukces, o którym marzysz",
    # --- Korporacyjne ---
    "transformacja cyfrowa",
    "synergia",
    "holistyczne podejście",
    "kluczowe znaczenie",
    "niepodważalne korzyści",
    "optymalizacja procesów",
    "skalowanie biznesu",
    "leverage'owanie zasobów",
    # --- Przymiotniki (AI-speak) ---
    "niesamowity",
    "fantastyczny",
    "rewelacyjny",
    "wyjątkowy",
    "innowacyjny",
    # --- Konstrukcje manipulacyjne ---
    "czy kiedykolwiek zastanawiałeś się",
    "prawda jest taka, że",
    "sekretem sukcesu jest",
    "eksperci twierdzą",
    "badania pokazują",
    # --- Frazy produktowe AI (e-commerce PL) ---
    "idealnie wkomponuje się",
    "podkreśli charakter",
    "doskonale sprawdzi się",
    "nada elegancji",
    "premium jakość",
    "najwyższej jakości",
    "wyjątkowy design",
    "ponadczasowy styl",
    "perfekcyjnie wykonany",
    "unikalny produkt",
    "luksusowe wykończenie",
    "harmonijnie łączy",
    "estetyka i funkcjonalność",
    "wyrafinowany styl",
    # --- Frazy produktowe AI (Allegro PL, uzupełnienie) ---
    "must have",
    "hit sprzedażowy",
    "niezawodna jakość",
    "najwyższy standard",
    "dopracowany w każdym detalu",
    "solidne wykonanie",
    "elegancki wygląd",
    "nowoczesny design",
    "stylowy",
    "na długie lata",
    # --- Rozszerzenie po audycie copy v3 ---
    "idealny wybór",
    "doskonały wybór",
    "z najwyższej półki",
    "spraw sobie przyjemność",
    "nie pożałujesz",
    "prawdziwa gratka",
    "to coś więcej niż",
    "postaw na jakość",
    "zadbaj o",
    "przekonaj się sam",
    "gwarancja satysfakcji",
    "kompleksowe rozwiązanie",
    "niezwykle",
    "znakomity",
    "perfekcyjny",
    "nadaje charakteru",
    "odmień swoją kuchnię",
    "serce domu",
]


def check_ban_list(text: str) -> list[str]:
    """Sprawdza tekst i zwraca listę znalezionych zakazanych fraz (case-insensitive)."""
    text_lower = text.lower()
    found = []
    for phrase in BAN_LIST_ECOMMERCE:
        if phrase.lower() in text_lower:
            found.append(phrase)
    return found


# ---------------------------------------------------------------------------
# Prompty grafik
# ---------------------------------------------------------------------------

def get_image_prompts(kategoria, kolor_zlew="Czarny nakrapiany",
                      kolor_bateria="Czarno-złota",
                      kolor_syfon="Złoty",
                      kolor_dozownik="Złoty",
                      catalog_name="granitowe_zlewy"):
    """Generuje prompty do obrazow dopasowane do kategorii, kolorystyki i katalogu."""

    # Backward compat: LED i inne katalogi
    if catalog_name != "granitowe_zlewy":
        kolor_map = get_kolor_map(catalog_name)
        k = kolor_map.get(kolor_zlew, list(kolor_map.values())[0] if kolor_map else {
            "accent": "black-gold", "metal": "gold", "sink": "black granite"
        })
        accent, metal, sink = k.get("accent", "gold"), k.get("metal", "gold"), k.get("sink", "black granite")
        siphon_metal = metal
        dispenser_metal = metal
    else:
        # Granitowe Zlewy: osobne kolory per element
        kolory_pe = get_kolory_per_element(catalog_name)
        sink_map = kolory_pe.get("kolor_zlew", {}).get(kolor_zlew, {"sink": "black speckled granite"})
        bat_map = kolory_pe.get("kolor_bateria", {}).get(kolor_bateria, {"accent": "black-gold", "metal": "gold"})
        syf_map = kolory_pe.get("kolor_syfon_widoczny", {}).get(kolor_syfon, {"metal": "gold"})
        doz_map = kolory_pe.get("kolor_dozownik", {}).get(kolor_dozownik, {"metal": "gold"})

        sink = sink_map["sink"]
        accent = bat_map["accent"]
        metal = bat_map["metal"]
        siphon_metal = syf_map["metal"]
        dispenser_metal = doz_map["metal"]

    no_text = "Do NOT add any text, labels, watermarks, or annotations to the image."
    color_rule = (
        f"CRITICAL COLOR RULE: Faucet and its handle MUST be {accent}. "
        f"Siphon drain ring visible in sink MUST be {siphon_metal}. "
        f"Soap dispenser pump MUST be {dispenser_metal}. "
        f"Each element has its own color finish - do NOT make them all the same."
    )
    studio = "White studio background, professional lighting, soft shadows. E-commerce product photography, high resolution."
    quality = "Crystal sharp focus, professional color grading, realistic material textures. Aspect ratio: 4:3 landscape (1200x900px)."
    negative = (
        "NEVER: text overlays, watermarks, plastic sheen on granite, blurry edges, "
        "floating objects, AI artifacts, distorted proportions, extra faucets or sinks."
    )
    fidelity = (
        "CRITICAL FIDELITY RULE: You are working with a REFERENCE PHOTO of the real product. "
        "You MUST preserve the EXACT product structure from the reference image. "
        "If the sink has a drainboard (ociekacz), the generated image MUST include the drainboard. "
        "If the sink has two bowls, show two bowls. Do NOT simplify, remove parts, "
        "change the number of bowls, or alter the product configuration in ANY way. "
        "The product in the output MUST be structurally identical to the reference photo."
    )
    material = (
        "MATERIAL ACCURACY: granite = matte stone texture with visible mineral speckles, "
        "NOT plastic, NOT ceramic gloss. Metal parts = realistic metallic reflections "
        "matching specified finish."
    )

    kat = kategoria.lower()

    # --- Katalog LED ---
    if catalog_name == "led_oswietlenie":
        return _get_led_prompts(kat, accent, metal, studio, no_text)

    # --- Katalog Granitowe Zlewy ---
    zestawy = []
    lifestyle = []

    if "zlew" in kat and "bateria" not in kat and "zestaw" not in kat:
        zestawy = [
            {"name": "Zlew (widok z gory)",
             "prompt": f"Professional product photo of a {sink} kitchen sink. Top-down view. {fidelity} {studio} {quality} {material} {color_rule} {negative} {no_text}"},
            {"name": "Zlew (kat 3/4)",
             "prompt": f"Professional product photo of a {sink} kitchen sink from 3/4 angle showing depth. {fidelity} {studio} {quality} {material} {color_rule} {negative} {no_text}"},
        ]
    elif "bateria" in kat and "zlew" not in kat and "zestaw" not in kat:
        zestawy = [
            {"name": "Bateria (frontalnie)",
             "prompt": f"Professional product photo of a {accent} kitchen faucet. Front view, full height. {fidelity} {studio} {quality} {material} {negative} {no_text}"},
            {"name": "Bateria (kat 3/4)",
             "prompt": f"Professional product photo of a {accent} kitchen faucet from 3/4 angle. {fidelity} {studio} {quality} {material} {negative} {no_text}"},
        ]
    elif "syfon" in kat and "zestaw" not in kat:
        zestawy = [
            {"name": "Syfon (studio)",
             "prompt": f"Professional product photo of a {siphon_metal} kitchen sink siphon/drain assembly. {fidelity} {studio} {quality} {material} {negative} {no_text}"},
        ]
    elif "dozownik" in kat and "zestaw" not in kat:
        zestawy = [
            {"name": "Dozownik (studio)",
             "prompt": f"Professional product photo of a {dispenser_metal} built-in kitchen countertop soap dispenser. {fidelity} {studio} {quality} {material} {negative} {no_text}"},
        ]
    elif "akcesori" in kat:
        zestawy = [
            {"name": "Akcesorium (studio)",
             "prompt": f"Professional product photo of this kitchen sink accessory. {fidelity} {studio} {quality} {negative} {no_text}"},
        ]
    else:
        extras = ""
        if "dozownik" in kat:
            extras += f", a matching {dispenser_metal} built-in soap dispenser"
        if "syfon" in kat:
            extras += f", a matching {siphon_metal} siphon drain"
        zestawy = [
            {"name": "Kompozycja zestawu (widok z gory)",
             "prompt": (
                 f"Create a professional product composition photo. "
                 f"Combine this {sink} kitchen sink and this {accent} kitchen faucet{extras} "
                 f"into one cohesive product set photo. The faucet mounted on the sink naturally. "
                 f"Top-down view. {fidelity} {studio} {quality} {material} {color_rule} {negative} {no_text}"
             )},
            {"name": "Kompozycja zestawu (kat 3/4)",
             "prompt": (
                 f"Create a professional product composition photo. "
                 f"Combine this {sink} kitchen sink and this {accent} kitchen faucet{extras} "
                 f"into one cohesive product set photo. The faucet mounted on the sink naturally. "
                 f"3/4 angle view. {fidelity} {studio} {quality} {material} {color_rule} {negative} {no_text}"
             )},
        ]

    # --- Prompty lifestyle ---
    if "syfon" in kat and "zestaw" not in kat:
        _acc_metal = siphon_metal
    elif "dozownik" in kat and "zestaw" not in kat:
        _acc_metal = dispenser_metal
    else:
        _acc_metal = metal

    if ("syfon" in kat or "dozownik" in kat or "akcesori" in kat) and "zestaw" not in kat:
        lifestyle = [
            {"name": "Zainstalowane w kuchni",
             "prompt": (
                 f"Show this {_acc_metal} kitchen accessory installed in a modern kitchen. "
                 f"Close-up, marble countertop, natural light, warm atmosphere. "
                 f"Professional interior photography, 4K. {fidelity} {quality} {material} {color_rule} {negative} {no_text}"
             )},
        ]
    else:
        product = f"{sink} kitchen sink with {accent} faucet"
        if "zlew" in kat and "bateria" not in kat:
            product = f"{sink} kitchen sink"
        elif "bateria" in kat and "zlew" not in kat:
            product = f"{accent} kitchen faucet"

        lifestyle = [
            {"name": "Nowoczesna jasna kuchnia",
             "prompt": (
                 f"Place this {product} into a photorealistic modern kitchen scene. "
                 f"Bright marble or quartz countertop. Natural window light from the left. "
                 f"Small kitchen accessories nearby (olive oil bottle, herb pot, wooden cutting board). "
                 f"Warm, inviting atmosphere. Professional interior photography, 4K, shallow depth of field. "
                 f"{fidelity} {quality} {material} {color_rule} {negative} {no_text}"
             )},
            {"name": "Industrialna ciemna kuchnia",
             "prompt": (
                 f"Place this {product} into a photorealistic industrial style kitchen. "
                 f"Dark wood countertop, exposed brick wall, matte black fixtures, pendant Edison bulb. "
                 f"Moody atmosphere. Professional interior photography, 4K. "
                 f"{fidelity} {quality} {material} {color_rule} {negative} {no_text}"
             )},
            {"name": "Skandynawska kuchnia",
             "prompt": (
                 f"Place this {product} into a photorealistic scandinavian minimalist kitchen. "
                 f"Light oak countertop, white subway tiles, clean lines, lots of natural light. "
                 f"A small succulent plant nearby. Professional interior photography, 4K. "
                 f"{fidelity} {quality} {material} {color_rule} {negative} {no_text}"
             )},
            {"name": "Kuchnia rustykalna",
             "prompt": (
                 f"Place this {product} into a photorealistic rustic farmhouse kitchen. "
                 f"Warm wooden countertop, terracotta tiles, copper pots on wall hooks, "
                 f"fresh herbs in ceramic pots, warm golden light from window. "
                 f"Professional interior photography, 4K. "
                 f"{fidelity} {quality} {material} {color_rule} {negative} {no_text}"
             )},
            {"name": "Kuchnia premium ciemna",
             "prompt": (
                 f"Place this {product} into a photorealistic luxury dark kitchen. "
                 f"Black marble countertop, dark matte cabinets, gold accent lighting, "
                 f"high-end appliances visible in background. Dramatic moody lighting. "
                 f"Professional interior photography, 4K. "
                 f"{fidelity} {quality} {material} {color_rule} {negative} {no_text}"
             )},
        ]

    return zestawy, lifestyle


def _get_led_prompts(kat, accent, metal, studio, no_text):
    """Prompty dla katalogu LED."""
    zestawy = []
    lifestyle = []

    if "panel" in kat:
        zestawy = [
            {"name": "Panel LED (studio)",
             "prompt": f"Professional product photo of an LED panel light. Front view showing the light surface. {studio} {no_text}"},
            {"name": "Panel LED (kat 3/4)",
             "prompt": f"Professional product photo of an LED panel light from 3/4 angle showing slim profile. {studio} {no_text}"},
        ]
        lifestyle = [
            {"name": "Panel w biurze",
             "prompt": f"Show this LED panel light installed in a modern office ceiling. Clean, bright workspace, white desk, laptop. Professional interior photography, 4K. {no_text}"},
        ]
    elif "tasma" in kat or "taśma" in kat:
        zestawy = [
            {"name": "Tasma LED (studio)",
             "prompt": f"Professional product photo of an LED strip light on a reel. {studio} {no_text}"},
        ]
        lifestyle = [
            {"name": "Tasma pod szafkami",
             "prompt": f"Show this LED strip light installed under kitchen cabinets, illuminating a marble countertop. Warm atmosphere, modern kitchen. Professional interior photography, 4K. {no_text}"},
            {"name": "Tasma w salonie",
             "prompt": f"Show this LED strip light as ambient lighting in a modern living room. Behind TV, under floating shelves. Cozy evening atmosphere. Professional interior photography, 4K. {no_text}"},
        ]
    elif "profil" in kat:
        zestawy = [
            {"name": "Profil aluminiowy (studio)",
             "prompt": f"Professional product photo of an aluminum LED profile/channel with diffuser cover. {studio} {no_text}"},
        ]
        lifestyle = [
            {"name": "Profil zainstalowany",
             "prompt": f"Show this aluminum LED profile installed with LED strip inside, creating a clean line of light. Modern interior, close-up. Professional photography, 4K. {no_text}"},
        ]
    elif "zasilacz" in kat:
        zestawy = [
            {"name": "Zasilacz LED (studio)",
             "prompt": f"Professional product photo of an LED power supply / transformer. {studio} {no_text}"},
        ]
        lifestyle = []
    elif "sterownik" in kat or "ściemniacz" in kat:
        zestawy = [
            {"name": "Sterownik (studio)",
             "prompt": f"Professional product photo of an LED controller/dimmer with remote control. {studio} {no_text}"},
        ]
        lifestyle = []
    elif "oprawa" in kat:
        zestawy = [
            {"name": "Oprawa LED (studio)",
             "prompt": f"Professional product photo of an LED downlight/fixture. Front view. {studio} {no_text}"},
            {"name": "Oprawa LED (profil)",
             "prompt": f"Professional product photo of an LED downlight/fixture from side angle showing slim profile. {studio} {no_text}"},
        ]
        lifestyle = [
            {"name": "Oprawa w suficie",
             "prompt": f"Show this LED downlight installed in a white ceiling of a modern bathroom. Clean, bright atmosphere. Professional interior photography, 4K. {no_text}"},
        ]
    else:
        zestawy = [
            {"name": "Akcesorium LED (studio)",
             "prompt": f"Professional product photo of this LED accessory/connector. {studio} {no_text}"},
        ]
        lifestyle = []

    return zestawy, lifestyle


# ---------------------------------------------------------------------------
# Prompt opisu B2C
# ---------------------------------------------------------------------------

def _build_color_info(kolor_zlew, kolor_bateria, kolor_syfon, kolor_dozownik):
    """Buduje string info o kolorach elementów do promptu opisu."""
    parts = []
    if kolor_zlew:
        parts.append(f"Kolor zlewu: {kolor_zlew}")
    if kolor_bateria:
        parts.append(f"Kolor baterii: {kolor_bateria}")
    if kolor_syfon:
        parts.append(f"Kolor syfonu (widoczna część): {kolor_syfon}")
    if kolor_dozownik:
        parts.append(f"Kolor dozownika: {kolor_dozownik}")
    if parts:
        return f"KOLORY ELEMENTÓW: {'. '.join(parts)}."
    return ""


def generate_description_prompt(spec_text, kategoria="Zestaw", catalog_name="granitowe_zlewy",
                                kolor_zlew="", kolor_bateria="", kolor_syfon="", kolor_dozownik=""):
    """Prompt do generowania opisu B2C zoptymalizowanego pod Allegro SEO."""
    seo = get_seo_data(catalog_name, kategoria)
    if not seo:
        seo = {
            "frazy": [],
            "tytul_przyklady": [],
            "parametry_obowiazkowe": "stan, marka",
            "parametry_opcjonalne": "",
            "opis_elementy": "",
            "usp": "",
        }

    frazy_str = ", ".join(seo["frazy"])
    tytuly_str = "\n".join(f"  - {t}" for t in seo["tytul_przyklady"])

    target_audience = "KOBIET 25-55 lat, które urządzają lub remontują kuchnię"
    if catalog_name == "led_oswietlenie":
        target_audience = "osób urządzających dom, remontujących lub szukających nowoczesnego oświetlenia"

    return f"""Jesteś doświadczoną sprzedawczynią w sklepie z wyposażeniem kuchni.
Piszesz opisy produktów na Allegro. Twoje opisy brzmią jak napisane przez człowieka, nie przez AI.
Piszesz dla {target_audience}.
Ton: ciepły, konkretny, praktyczny. Jak gdybyś tłumaczyła klientce w sklepie stacjonarnym.
KRYTYCZNE: Pisz WYŁĄCZNIE po polsku. Nawet jeśli specyfikacja jest w innym języku, przetłumacz i pisz po polsku. Żadnych angielskich słów.

PRZYKŁAD ZŁEGO AKAPITU (NIE pisz tak):
"Ten wyjątkowy zlewozmywak idealnie wkomponuje się w każdą kuchnię. Doskonale sprawdzi się zarówno w małych, jak i dużych wnętrzach. Premium jakość i ponadczasowy styl."

PRZYKŁAD DOBREGO AKAPITU (pisz TAK):
"Jedna głęboka komora (185 mm) zmieści dużą patelnię i blachę do pieczenia. 80% granitu w składzie, nie zarysuje się od garnków. Czarny z nakrapieniem, nie widać kamienia."

SPECYFIKACJA PRODUKTU:
{spec_text}

KATEGORIA: {kategoria}
{_build_color_info(kolor_zlew, kolor_bateria, kolor_syfon, kolor_dozownik)}
USP SKLEPU (OBOWIĄZKOWO w opisie i bullet points):
{seo["usp"]}

FRAZY KLUCZOWE ALLEGRO (wplataj naturalnie w tytuł i opis, BEZ keyword stuffingu):
{frazy_str}

NAPISZ dokładnie te sekcje (każda oznaczona nagłówkiem ##):

## TYTUŁ ALLEGRO
DOKŁADNIE 60-75 znaków (poniżej 60 = zbyt krótki, strata SEO. Powyżej 75 = Allegro ucina). Podaj liczbę znaków w [XX zn.] po tytule. Słowa kluczowe NA POCZĄTKU.
Dla zestawów: ZAWSZE zacznij od "Zestaw zlew granitowy" lub "Zlewozmywak granitowy".
Struktura: Typ produktu → Marka/Model → Cechy (materiał/kolor/wymiar) → Dodatki
ZAKAZANE w tytule: "tanio", "okazja", "nowość", "promocja", "hit", CAPS LOCK, przymiotniki na początku, wykrzykniki.
WZORY (dopasuj do specyfikacji):
{tytuly_str}

## OPIS HTML
400-600 słów. Gotowy HTML do wklejenia na Allegro.
Dozwolone tagi: h2, p, ul, ol, li, b, strong. ZAKAZANE: h1, div, span, style, class, img.
Max 40 000 bajtów. Max 100 sekcji.

STRUKTURA (dokładnie w tej kolejności):
1. NAGŁÓWEK h2 z emoji + GŁÓWNA KORZYŚĆ (2-3 zdania emocjonalne, jak produkt zmieni kuchnię kupującej)
2. KLUCZOWE KORZYŚCI (lista ul/li, 5-7 bullet points: ✅ <b>cecha</b> · korzyść życiowa)
3. SPECYFIKACJA TECHNICZNA (lista ul/li z parametrami: {seo["opis_elementy"]})
4. CO DOSTAJESZ W ZESTAWIE (lista ul/li elementów w paczce)
5. FAQ (3-4 pytania h2 z emoji + odpowiedzi p, zbijające obiekcje: nawiercanie, odporność, zwroty)
6. INFORMACJA O DOSTAWIE (p: wysyłka 24h, darmowa dostawa od 999 zł, Allegro Smart)

EMOTIKONY W NAGŁÓWKACH (obowiązkowe):
- Każdy nagłówek h2 MUSI zaczynać się od 1 emoji pasującego do treści
- Max 1 emoji per nagłówek, NIE w body tekstu
- Bullet points korzyści zaczynaj od ✅ (nie myślnik, nie kropka)

STYL PISANIA:
- Otwieraj emocją i korzyścią życiową, NIE suchą specyfikacją
- Krótkie akapity (4-6 linii), nagłówki h2, wypunktowania
- Konkretne liczby zamiast przymiotników ("185 mm głębokości", NIE "głęboki")
- Zero marketingowego bełkotu, zero CAPS LOCK, zero "!!!"
- Po polsku, naturalnie, jakby pisała doświadczona sprzedawczyni

CHECKLIST B2C (każdy opis MUSI spełniać):
- Korzyści > cechy (nie "185mm głębokości" ale "185mm głębokości, zmieści każdy garnek")
- Emocja + logika (otwierasz emocją, zamykasz parametrem)
- Social proof (OBOWIĄZKOWE, NIE POMIJAJ: dodaj dokładnie 1 zdanie z liczbą, np. "Ponad 400 zamówień miesięcznie" lub "Zaufało nam ponad 4 000 klientów z całej Polski". Umieść w sekcji otwarcia LUB jako osobny akapit przed CTA)
- CTA (OBOWIĄZKOWE na samym końcu opisu, OSTATNI element: "Dodaj do koszyka i zamów z darmową dostawą" lub "Masz pytania? Napisz, odpowiadamy w 24h". BEZ: "Kup teraz!!!", "Nie czekaj!", "Ostatnie sztuki!". Jeśli brak CTA na końcu = opis NIEKOMPLETNY)
- FAQ zbijające top 3 obiekcje kupujących
- Gwarancja zwrotu (14 dni bez podania przyczyny)

ZAKAZANE FRAZY (NIGDY nie używaj):
- idealnie wkomponuje się, podkreśli charakter, doskonale sprawdzi się, nada elegancji
- premium jakość, najwyższej jakości, wyjątkowy design, ponadczasowy styl
- perfekcyjnie wykonany, unikalny produkt, luksusowe wykończenie
- harmonijnie łączy, estetyka i funkcjonalność, wyrafinowany styl
- niesamowity, fantastyczny, rewelacyjny, wyjątkowy, innowacyjny
- przełomowe rozwiązanie, rewolucyjne podejście, holistyczne podejście
- uwolnij swój potencjał, wykorzystaj moc, odkryj sekrety
ZAMIAST zakazanych fraz pisz tak:
- "idealnie wkomponuje się" → opisz wymiary i kolor konkretnie: "zlew 79x50, czarny, pasuje do szafki od 50 cm"
- "doskonale sprawdzi się" → podaj sytuację: "zmieści patelnię 28 cm i blachę do pieczenia"
- "premium jakość" → podaj skład: "80% kruszywo granitowe, odporność na zarysowania"
- "ponadczasowy styl" → opisz co widać: "czarny mat z delikatnym nakrapieniem"
Pisz naturalnie, jakby pisała doświadczona sprzedawczyni. Zero AI-speak.

## PARAMETRY JSON
Obiekt JSON z parametrami technicznymi produktu dla Allegro.
Obowiązkowe parametry Allegro dla tej kategorii: {seo["parametry_obowiazkowe"]}
Opcjonalne (ale WARTO wypełnić, wpływają na filtry): {seo["parametry_opcjonalne"]}
Format przykładowy: {{"kolor": "czarny", "material": "granit", "marka": "GranitoweZlewy"}}
Podaj TYLKO parametry które wynikają ze specyfikacji. Nie wymyślaj.

## BULLET POINTS
5-8 punktów. Każdy MUSI zaczynać się od ✅ (emoji checkmark).
Format: ✅ **Cecha** · korzyść dla klientki
OBOWIĄZKOWO uwzględnij USP.

## SKU
Zaproponuj kod SKU w formacie: TYP-MODEL-KOLOR (np. ZLEW-MOD8050-CZ, BAT-FLEX-CZZL)"""


# ---------------------------------------------------------------------------
# Parser sekcji
# ---------------------------------------------------------------------------

def parse_description_sections(desc_text):
    """Parsuje wygenerowany opis na sekcje."""
    sections = {
        "tytul": "", "opis": "", "parametry_json": "",
        "bullets": "", "sku": "",
    }
    current = ""
    for line in desc_text.split("\n"):
        lower = line.lower().strip()
        if "tytu" in lower and lower.startswith("#"):
            current = "tytul"
            continue
        elif "opis html" in lower and lower.startswith("#"):
            current = "opis"
            continue
        elif "parametry json" in lower and lower.startswith("#"):
            current = "parametry_json"
            continue
        elif "parametr" in lower and lower.startswith("#") and "json" not in lower:
            current = "parametry_json"
            continue
        elif "bullet" in lower and lower.startswith("#"):
            current = "bullets"
            continue
        elif "sku" in lower and lower.startswith("#"):
            current = "sku"
            continue
        if current:
            sections[current] += line + "\n"

    for key in sections:
        sections[key] = sections[key].strip()

    params_dict = {}
    if sections["parametry_json"]:
        raw = sections["parametry_json"]
        if "```" in raw:
            parts = raw.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    raw = part
                    break
        try:
            params_dict = json.loads(raw)
        except json.JSONDecodeError:
            pass
    sections["parametry_dict"] = params_dict

    return sections


# ---------------------------------------------------------------------------
# Prompt ekstrakcji danych ze specyfikacji
# ---------------------------------------------------------------------------

def get_extraction_prompt(spec_text: str) -> str:
    """Prompt do ekstrakcji danych ze specyfikacji produktu."""
    return f"""Przeanalizuj poniższą specyfikację produktu i wyekstrahuj dane do formatu JSON.

SPECYFIKACJA:
{spec_text}

WYEKSTRAHUJ następujące pola (podaj TYLKO wartości WYRAŹNIE OBECNE w specyfikacji, brak = null):

{{
  "waga_kg": number lub null,
  "wysokosc_cm": number lub null,
  "szerokosc_cm": number lub null,
  "dlugosc_cm": number lub null,
  "material": string lub null,
  "kolor": string lub null,
  "kolor_zlew": string lub null,
  "kolor_bateria": string lub null,
  "kolor_syfon_widoczny": string lub null,
  "kolor_dozownik": string lub null,
  "typ_montazu": string lub null,
  "srednica_odplywu": string lub null,
  "min_szafka_cm": number lub null,
  "glebokosc_komory_mm": number lub null,
  "model": string lub null,
  "marka": string lub null,
  "ean": string lub null,
  "kategoria_sugerowana": string lub null
}}

DOZWOLONE WARTOŚCI "kategoria_sugerowana" (wybierz JEDNĄ lub null):
- "Zestaw (zlew + bateria + syfon)"
- "Zestaw (zlew + bateria)"
- "Zestaw (zlew + bateria + dozownik + syfon)"
- "Zlew granitowy"
- "Bateria kuchenna"
- "Syfon"
- "Dozownik płynu"
- "Akcesoria (wężyk / ruszt / kratka)"
- "Panel LED"
- "Taśma LED"
- "Profil aluminiowy"
- "Zasilacz LED"
- "Sterownik / Ściemniacz"
- "Oprawa LED"
- "Akcesoria LED"

ZASADY:
1. Podaj TYLKO wartości wyraźnie obecne w specyfikacji
2. Jeśli wartość nie jest podana wprost - zwróć null
3. Przelicz jednostki: wymiary na cm, waga na kg, głębokość komory na mm
4. Odpowiedz TYLKO obiektem JSON, bez dodatkowego tekstu
"""


# ---------------------------------------------------------------------------
# Prompt regeneracji grafik
# ---------------------------------------------------------------------------

def get_regen_prompt(mode: str, instruction: str, product_context: str = "") -> str:
    """Generuje prompt do regeneracji grafiki.

    mode: "edit" (drobna poprawka) lub "full" (od nowa)
    instruction: co zmienić (od użytkownika)
    product_context: kontekst produktu (kategoria, kolor)
    """
    context_block = ""
    if product_context:
        context_block = f"\nPRODUCT CONTEXT: {product_context}\n"

    if mode == "edit":
        return f"""EDIT MODE: Minor adjustment to the existing image.
{context_block}
INSTRUCTION: {instruction}

CRITICAL RULES:
- Modify ONLY the specified element.
- Keep all other elements, composition, lighting, and background EXACTLY the same.
- Do not add any new objects or elements.
- Do not change the camera angle, perspective, or framing.
- Preserve the original color palette, shadows, and reflections.
- PRODUCT FIDELITY: Preserve the EXACT product structure. If the sink has a drainboard, keep the drainboard. Do NOT simplify, remove parts, or change the product configuration.
- The result should look like the same photo with one small change."""

    elif mode == "full":
        return f"""FULL REGENERATION: Create a completely new image from scratch.
{context_block}
INSTRUCTION: {instruction}

RULES:
- Generate a fresh composition based on the instruction and product context.
- Use source/reference images for product accuracy (shape, color, proportions).
- PRODUCT FIDELITY: Preserve the EXACT product structure from the reference. If the sink has a drainboard, include the drainboard. Do NOT simplify or remove parts.
- New scene, lighting, and arrangement are allowed and encouraged.
- Maintain professional e-commerce photography quality.
- Follow all color consistency rules from the original prompt."""

    else:
        raise ValueError(f"Nieznany tryb regeneracji: {mode!r}. Dozwolone: 'edit', 'full'.")


# ---------------------------------------------------------------------------
# Prompt poprawki opisu
# ---------------------------------------------------------------------------

def get_description_revision_prompt(current_html: str, instruction: str, ban_list_subset: list[str] | None = None) -> str:
    """Prompt do poprawki opisu aukcji przez AI.

    Args:
        current_html: aktualny opis HTML
        instruction: instrukcja poprawki od użytkownika
        ban_list_subset: podzbiór ban listy (domyślnie top 20)
    """
    instruction = instruction[:500]
    instruction = re.sub(r'[<>{}]', '', instruction)
    if ban_list_subset is None:
        ban_list_subset = BAN_LIST_ECOMMERCE[:20]
    ban_str = ", ".join(f'"{f}"' for f in ban_list_subset)
    return f"""Oto aktualny opis aukcji Allegro w HTML:

{current_html}

Użytkownik prosi o zmianę: {instruction}

ZASADY:
1. Zwróć CAŁY poprawiony opis HTML (nie fragment, cały dokument od pierwszego <h2> do ostatniego </p>)
2. Zachowaj strukturę sekcji (nagłówki h2, listy ul/li, akapity p)
3. Dozwolone tagi: h2, h3, p, ul, ol, li, b, strong, br, em, small
4. ZAKAZANE tagi: h1, div, span, style, class, img, script
5. NIE dodawaj fraz z BAN LISTY: {ban_str}
6. Pisz po polsku, naturalnie, jak doświadczona sprzedawczyni
7. Odpowiedz TYLKO kodem HTML, bez dodatkowego tekstu, bez ```html bloków, bez komentarzy
8. Zachowaj emotikony w nagłówkach h2 (jeśli były)
9. Zachowaj bullet points z ✅ (jeśli były)"""


# ---------------------------------------------------------------------------
# Testy
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # 1. Test check_ban_list
    sample = (
        "Ten zlew to niesamowity produkt premium jakość. "
        "Doskonale sprawdzi się w każdej kuchni. "
        "Wyjątkowy design i luksusowe wykończenie."
    )
    found = check_ban_list(sample)
    assert "niesamowity" in found, f"Brak 'niesamowity' w {found}"
    assert "premium jakość" in found, f"Brak 'premium jakość' w {found}"
    assert "doskonale sprawdzi się" in found, f"Brak 'doskonale sprawdzi się' w {found}"
    assert "wyjątkowy" in found, f"Brak 'wyjątkowy' w {found}"
    assert "luksusowe wykończenie" in found, f"Brak 'luksusowe wykończenie' w {found}"
    print(f"check_ban_list: OK ({len(found)} fraz znalezionych: {found})")

    clean = "Zlew granitowy jednokomorowy 80x50 cm z ociekaczem. Głębokość komory 185 mm."
    found_clean = check_ban_list(clean)
    assert len(found_clean) == 0, f"False positive: {found_clean}"
    print(f"check_ban_list (czysty tekst): OK (0 fraz)")

    # 2. Test get_extraction_prompt
    spec = "Zlew granitowy 80x50, waga 12kg, kolor czarny, marka GranitoweZlewy"
    prompt = get_extraction_prompt(spec)
    assert "SPECYFIKACJA:" in prompt
    assert spec in prompt
    assert '"waga_kg"' in prompt
    assert '"material"' in prompt
    print("get_extraction_prompt: OK")

    # 3. Test get_regen_prompt (edit)
    regen_edit = get_regen_prompt("edit", "Zmień kolor baterii na złoty", "zlew czarny 80x50")
    assert "EDIT MODE" in regen_edit
    assert "Modify ONLY" in regen_edit
    assert "Zmień kolor baterii na złoty" in regen_edit
    assert "zlew czarny 80x50" in regen_edit
    print("get_regen_prompt (edit): OK")

    # 4. Test get_regen_prompt (full)
    regen_full = get_regen_prompt("full", "Wygeneruj zdjęcie w skandynawskiej kuchni")
    assert "FULL REGENERATION" in regen_full
    assert "Wygeneruj zdjęcie w skandynawskiej kuchni" in regen_full
    print("get_regen_prompt (full): OK")

    # 5. Test get_regen_prompt (błędny tryb)
    try:
        get_regen_prompt("invalid", "test")
        assert False, "Powinien rzucić ValueError"
    except ValueError:
        print("get_regen_prompt (błędny tryb): OK (ValueError)")

    # 6. Test get_description_revision_prompt
    sample_html = "<h2>Test</h2><p>Opis produktu</p>"
    rev_prompt = get_description_revision_prompt(sample_html, "Zmień nagłówek")
    assert sample_html in rev_prompt, "Brak current_html w prompcie"
    assert "Zmień nagłówek" in rev_prompt, "Brak instrukcji w prompcie"
    assert "BAN LISTY" in rev_prompt, "Brak ban listy w prompcie"
    print("get_description_revision_prompt: OK")

    # 7. Test get_description_revision_prompt z custom ban list
    custom_ban = ["fraza1", "fraza2"]
    rev_prompt2 = get_description_revision_prompt(sample_html, "Test", ban_list_subset=custom_ban)
    assert '"fraza1"' in rev_prompt2, "Brak custom ban list"
    assert '"fraza2"' in rev_prompt2, "Brak custom ban list"
    print("get_description_revision_prompt (custom ban): OK")

    # 8. Test get_description_revision_prompt z pustym HTML
    rev_prompt3 = get_description_revision_prompt("", "Napisz nowy opis")
    assert "Napisz nowy opis" in rev_prompt3
    print("get_description_revision_prompt (pusty HTML): OK")

    print(f"\nALL TESTS PASSED ({8} tests)")
