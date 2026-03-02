"""
Prompty do generowania grafik i opisów produktowych.

Obsługuje różne katalogi przez import z catalogs.py.
"""

import json
import logging
import re
from catalogs import get_kolor_map, get_kolory_per_element, get_seo_data, get_seo_key

logger = logging.getLogger(__name__)


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
# Pipeline v4.3: Bloki stałe do promptów (reużywalne)
# ---------------------------------------------------------------------------

DSLR_REALISM_BLOCK = (
    "REAL PHOTOGRAPH Canon EOS R5 / Nikon Z8. Natural daylight 5500K. "
    "NOT 3D render, NOT CGI, NOT AI-generated. "
    "Imperfections: uneven grout, water droplets, subtle grain ISO 400, "
    "dust in raking light. Realistic contact shadow under product."
)

SHADOW_REFLECTION_BLOCK = (
    "SHADOW AND REFLECTION: realistic contact shadow under product, "
    "subtle reflection on wet granite surface, natural light interaction. "
    "NOT floating, NOT sticker-pasted, NOT composited look."
)

MATERIAL_ACCURACY_BLOCK = (
    "granite = matte stone, mineral speckles. NOT plastic, NOT ceramic. "
    "Metal = realistic reflections. Water on granite = beading, "
    "natural contact shadow."
)

BANNED_PHRASES_BLOCK = (
    "NEVER: moody, dramatic, luxury, premium, high-end, elegant, "
    "golden hour, cinematic, ethereal, artisanal."
)

PRESERVATION_LIST_BLOCK = (
    "PRESERVATION LIST: product shape, dimensions, bowl count, "
    "drainboard position, faucet hole placement, color tone, "
    "surface texture, hardware finish. Extreme accuracy required. "
    "DO NOT alter, stylize, or reinterpret any product feature."
)


def get_style_lock_block(style_lock_id: str | None) -> str:
    """Reużywalny blok spójności stylu między obrazami jednego joba."""
    lock_id = style_lock_id or "default-style-lock"
    return (
        f"=== STYLE LOCK (ID: {lock_id}) ===\n"
        "Keep the same visual family across all images in this job:\n"
        "- neutral commercial color grading (no cinematic tint),\n"
        "- white balance around 5400K and consistent contrast curve,\n"
        "- soft key light from 45° left with gentle opposite fill,\n"
        "- realistic contact shadows, no synthetic hard edges,\n"
        "- photoreal e-commerce look (not editorial mood).\n"
        "If previous images exist for this STYLE LOCK ID, match their lighting softness, "
        "perspective discipline, and color response."
    )


# Elementy niezbędne w realistycznej scenie kuchennej (auto-kompletowanie)
ESSENTIAL_SCENE_ELEMENTS = {
    "bateria": "color-matched kitchen faucet",
    # syfon, deska do krojenia - nie widoczne w lifestyle overhead, pomijaj
}


def resolve_scene_elements(dna: dict, allow_auto_suggestions: bool = True) -> tuple[str, str, list[str]]:
    """Centralna logika: co dodać do sceny, co wykluczyć, co auto-suggested.

    Używana przez build_product_dna_enforcement(), get_lifestyle_prompt_v2()
    i pipeline_lifestyle.py. Jedna funkcja = zero ryzyka rozjazdu.

    Returns: (include_str, exclude_str, auto_suggested_list)
    """
    visible = dna.get("visible_elements", [])
    not_present = dna.get("NOT_present", [])
    color = dna.get("color", "")

    # Sanityzacja: usuń z NOT_present elementy które są w visible (merge może dać konflikty)
    visible_lower = {v.lower().strip() for v in visible}
    not_present = [
        e for e in not_present
        if not any(v in e.lower() or e.lower() in v for v in visible_lower)
    ]

    auto_suggested = []
    if allow_auto_suggestions:
        for element, desc_tpl in ESSENTIAL_SCENE_ELEMENTS.items():
            is_missing = any(element in e.lower() for e in not_present)
            is_present = any(element in e.lower() for e in visible)
            if is_missing and not is_present:
                color_hint = f" in color matching {color}" if color else ""
                suggestion = f"{desc_tpl}{color_hint}"
                auto_suggested.append(suggestion)

    include_items = list(visible) + auto_suggested
    include_str = ", ".join(include_items) if include_items else "all elements from reference"

    if allow_auto_suggestions:
        filtered_exclude = [
            e for e in not_present
            if not any(key in e.lower() for key in ESSENTIAL_SCENE_ELEMENTS)
        ]
    else:
        filtered_exclude = list(not_present)
    exclude_str = ", ".join(filtered_exclude) if filtered_exclude else "nothing extra"

    return include_str, exclude_str, auto_suggested


def build_product_dna_enforcement(dna: dict, allow_auto_suggestions: bool = False) -> str:
    """Buduje blok PRODUCT DNA ENFORCEMENT z danych DNA."""
    bowl_count = dna.get("bowl_count", "unknown")
    shape = dna.get("bowl_shape", dna.get("shape", "unknown"))
    color = dna.get("color", "unknown")
    has_drainboard = dna.get("has_drainboard", False)
    has_faucet_hole = dna.get("has_faucet_hole", False)
    material_texture = dna.get("material_texture", "granitowy")

    drainboard_rule = "WITH drainboard" if has_drainboard else "NO drainboard"
    faucet_hole_rule = "WITH faucet hole" if has_faucet_hole else "NO faucet hole"
    visible_str, not_present_str, _ = resolve_scene_elements(
        dna, allow_auto_suggestions=allow_auto_suggestions
    )

    mounting = dna.get("mounting_type", "wpuszczany") or "wpuszczany"
    mounting_lower = mounting.lower().strip()

    if mounting_lower in ("wpuszczany", "drop-in", "top-mount"):
        mount_rule = (
            "INSTALLATION (CRITICAL): The sink MUST be shown as DROP-IN / FLUSH-MOUNTED "
            "into a precise rectangular cutout in the countertop. The sink rim sits flush "
            "with or slightly above the countertop surface. The bottom part / mounting "
            "trapezoid underneath MUST be completely HIDDEN below the countertop. "
            "Only the top rim, bowl interior, and drainboard are visible from above. "
            "The countertop surface seamlessly meets the sink edges. "
            "NEVER show the sink sitting ON TOP of the counter like a box."
        )
    elif mounting_lower in ("nablatowy", "vessel", "sit-on"):
        mount_rule = (
            "INSTALLATION: The sink is a VESSEL / SIT-ON type. It sits ON TOP of the countertop "
            "surface as a standalone basin. The full body of the sink is visible above the counter. "
            "Show it naturally placed on the countertop with the plumbing connection going down "
            "through a hole in the counter. This is correct - do NOT recess it into the counter."
        )
    elif mounting_lower in ("podwieszany", "undermount"):
        mount_rule = (
            "INSTALLATION (CRITICAL): The sink is UNDERMOUNT type. It is mounted BELOW the countertop. "
            "The countertop edge is visible around the sink opening with NO rim. The stone/granite "
            "countertop surface extends right to the edge of the cutout and the bowl drops below. "
            "The sink rim is NOT visible from above. Only the bowl interior is seen through the cutout."
        )
    else:
        logger.warning(f"Unknown mounting_type in Product DNA: '{mounting}'. Falling back to generic.")
        mount_rule = (
            f"Mounting type: {mounting}. Show the product installed in the most natural way "
            f"for this mounting type."
        )

    return (
        f"ABSOLUTE REQUIREMENT:\n"
        f"- EXACTLY {bowl_count} bowl(s), shape {shape}\n"
        f"- {drainboard_rule}, {faucet_hole_rule}\n"
        f"- Color {color} with {material_texture}\n"
        f"- ALL visible_elements: {visible_str}\n"
        f"- ZERO NOT_present: {not_present_str}\n"
        f"- {mount_rule}"
    )


# ---------------------------------------------------------------------------
# Prompty grafik
# ---------------------------------------------------------------------------

def get_image_prompts(kategoria, kolor_zlew="Czarny nakrapiany",
                      kolor_bateria="Czarno-złota",
                      kolor_syfon="Złoty",
                      kolor_dozownik="Złoty",
                      catalog_name="granitowe_zlewy"):
    """Generuje prompty do obrazów dopasowane do kategorii, kolorystyki i katalogu."""

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
        f"CRITICAL COLOR RULE (follow strictly): "
        f"The kitchen faucet body and handle MUST be {accent}, no other color. "
        f"The siphon drain ring visible in the sink opening MUST be {siphon_metal}. "
        f"The soap dispenser pump head MUST be {dispenser_metal}. "
        f"The sink basin material MUST be {sink}. "
        f"Each element has its own distinct color finish. Do NOT make all metal parts the same color."
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
        if "syfon" in kat:
            product += f", {siphon_metal} siphon drain"
        if "dozownik" in kat:
            product += f", {dispenser_metal} soap dispenser"
        if "zlew" in kat and "bateria" not in kat and "zestaw" not in kat:
            product = f"{sink} kitchen sink"
        elif "bateria" in kat and "zlew" not in kat and "zestaw" not in kat:
            product = f"{accent} kitchen faucet"

        lifestyle = [
            # --- Blat drewniany: 3 perspektywy ---
            {"name": "Drewno · overhead (z gory)",
             "prompt": (
                 f"{color_rule} "
                 f"Top-down overhead view, bird's eye perspective. "
                 f"Place this {product} into a photorealistic kitchen with a solid oak, beech or walnut wooden countertop "
                 f"with visible wood grain. Full composition visible from above. "
                 f"Everyday details on the counter: a coffee mug, fresh herbs in a small pot, "
                 f"a wooden cutting board with sliced bread, a linen dish towel folded nearby. "
                 f"Photojournalistic editorial kitchen photography style. Realistic imperfections, lived-in kitchen, "
                 f"natural daylight, real photograph not a 3D render. Warm neutral color temperature. "
                 f"{fidelity} {quality} {material} {negative} {no_text}"
             )},
            {"name": "Drewno · frontal (z boku)",
             "prompt": (
                 f"{color_rule} "
                 f"Eye-level front view, straight-on perspective. "
                 f"Place this {product} into a photorealistic kitchen with a solid oak, beech or walnut wooden countertop "
                 f"with visible wood grain. Sink as the central focal point. "
                 f"A window behind the sink with natural daylight streaming through. "
                 f"A linen dish towel draped on the countertop edge, spice jars on the side. "
                 f"Photojournalistic editorial kitchen photography style. Realistic imperfections, lived-in kitchen, "
                 f"natural daylight, real photograph not a 3D render. Warm neutral color temperature. "
                 f"{fidelity} {quality} {material} {negative} {no_text}"
             )},
            {"name": "Drewno · close-up (detal)",
             "prompt": (
                 f"{color_rule} "
                 f"Close-up macro detail shot, tight crop on sink and faucet. "
                 f"Place this {product} into a photorealistic kitchen with a solid oak, beech or walnut wooden countertop. "
                 f"Visible texture of granite sink basin and wood grain of the countertop in sharp focus. "
                 f"A few water droplets on the sink surface, realistic signs of everyday use. "
                 f"Photojournalistic editorial kitchen photography style. Realistic imperfections, lived-in kitchen, "
                 f"natural daylight, real photograph not a 3D render. Warm neutral color temperature. "
                 f"{fidelity} {quality} {material} {negative} {no_text}"
             )},
            # --- Blat granitowy: 3 perspektywy ---
            {"name": "Granit · overhead (z gory)",
             "prompt": (
                 f"{color_rule} "
                 f"Top-down overhead view, bird's eye perspective. "
                 f"Place this {product} into a photorealistic kitchen with a granite countertop (NOT marble). "
                 f"Full composition visible from above. "
                 f"Everyday details on the counter: a bowl of fresh fruit, a glass of water, "
                 f"a cookbook open on the side, a small ceramic dish with lemons. "
                 f"Photojournalistic editorial kitchen photography style. Realistic imperfections, lived-in kitchen, "
                 f"natural daylight, real photograph not a 3D render. Neutral color temperature. "
                 f"{fidelity} {quality} {material} {negative} {no_text}"
             )},
            {"name": "Granit · frontal (z boku)",
             "prompt": (
                 f"{color_rule} "
                 f"Eye-level front view, straight-on perspective. "
                 f"Place this {product} into a photorealistic kitchen with a granite countertop (NOT marble). "
                 f"Sink as the central focal point. "
                 f"Small succulents in ceramic pots on the side, neutral soft light from a side window. "
                 f"Photojournalistic editorial kitchen photography style. Realistic imperfections, lived-in kitchen, "
                 f"natural daylight, real photograph not a 3D render. Neutral color temperature. "
                 f"{fidelity} {quality} {material} {negative} {no_text}"
             )},
            {"name": "Granit · close-up (detal)",
             "prompt": (
                 f"{color_rule} "
                 f"Close-up macro detail shot, tight crop on sink and faucet. "
                 f"Place this {product} into a photorealistic kitchen with a granite countertop (NOT marble). "
                 f"Visible texture of granite countertop and granite sink basin in sharp focus. "
                 f"Realistic details: a few water droplets, faint soap residue near the drain. "
                 f"Photojournalistic editorial kitchen photography style. Realistic imperfections, lived-in kitchen, "
                 f"natural daylight, real photograph not a 3D render. Neutral color temperature. "
                 f"{fidelity} {quality} {material} {negative} {no_text}"
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

def get_analysis_prompt(
    spec_text: str,
    catalog_name: str,
    available_categories: list[str],
    available_colors: dict,
    required_features: list[str],
    user_notes: str = "",
) -> str:
    """Prompt do analizy produktu (nowy flow: analyze -> confirm -> generate).

    AI analizuje zdjęcia + specyfikację i zwraca sugestie kategorii, kolorów i features.
    """
    categories_str = "\n".join(f"  - {c}" for c in available_categories)

    colors_parts = []
    for element, color_map in available_colors.items():
        color_names = list(color_map.keys())
        colors_parts.append(f"  {element}: {', '.join(color_names)}")
    colors_str = "\n".join(colors_parts)

    features_str = ", ".join(required_features)

    notes_section = f"""
NOTATKI UŻYTKOWNIKA (kontekst, intencje, dodatkowe informacje):
{user_notes}
""" if user_notes else ""

    return f"""Analizujesz produkt z katalogu "{catalog_name}".
Na podstawie zdjęć i opisu produktu, zasugeruj parametry aukcji Allegro.

SPECYFIKACJA PRODUKTU:
{spec_text}
{notes_section}
DOSTĘPNE KATEGORIE (wybierz JEDNĄ najbardziej pasującą + max 2 alternatywy):
{categories_str}

DOSTĘPNE KOLORY PER ELEMENT:
{colors_str}

WYMAGANE FEATURES DLA TEJ KATEGORII:
{features_str}

Zwróć DOKŁADNIE taki JSON (bez dodatkowego tekstu, bez ```json bloków):
{{
  "kategoria": "nazwa kategorii z listy powyżej",
  "kategoria_alternatives": ["max 2 alternatywne kategorie"],
  "kolory": {{
    "zlew": "kolor z listy kolor_zlew lub null",
    "bateria": "kolor z listy kolor_bateria lub null",
    "syfon": "kolor z listy kolor_syfon_widoczny lub null",
    "dozownik": "kolor z listy kolor_dozownik lub null"
  }},
  "features": {{
    "nazwa_parametru": "wartość",
    "...": "..."
  }},
  "tytul_suggestion": "propozycja tytułu Allegro 60-75 znaków",
  "sku_suggestion": "propozycja SKU w formacie TYP-MODEL-KOLOR"
}}

ZASADY:
1. Kategorie i kolory MUSZĄ być z list powyżej (dokładne dopasowanie nazw)
2. Features: wypełnij TYLKO te które wynikają ze specyfikacji i zdjęć
3. Kolory: jeśli element nie występuje w produkcie, podaj null
4. Tytuł: 60-75 znaków, słowa kluczowe na początku, bez CAPS LOCK
5. SKU: format TYP-MODEL-KOLOR (np. ZLEW-SONGOS-CZ, BAT-FLEX-CZZL)
6. Odpowiedz TYLKO obiektem JSON"""


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
    instruction = instruction[:500]
    instruction = re.sub(r'[<>{}]', '', instruction)
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
# Pipeline v2: Product DNA + Lifestyle v2 + Self-check
# ---------------------------------------------------------------------------

LIFESTYLE_SCENES: list[dict] = [
    {
        "name": "Drewno · overhead",
        "countertop": "solid oak or walnut wooden",
        "perspective": "Top-down overhead view, bird's eye",
        "details": "coffee mug, fresh herbs in pot, wooden cutting board, linen towel",
    },
    {
        "name": "Drewno · frontal",
        "countertop": "solid oak or walnut wooden",
        "perspective": "Eye-level front view, straight-on",
        "details": "window with natural daylight behind, spice jars, linen towel draped on edge",
    },
    {
        "name": "Granit · overhead",
        "countertop": "granite (NOT marble)",
        "perspective": "Top-down overhead view, bird's eye",
        "details": "bowl of fresh fruit, glass of water, small ceramic dish with lemons",
    },
    {
        "name": "Granit · close-up",
        "countertop": "granite (NOT marble)",
        "perspective": "Close-up macro detail shot, tight crop",
        "details": "water droplets on surface, visible texture of countertop and product",
    },
    {
        "name": "W uzyciu",
        "countertop": "any light-colored",
        "perspective": "Eye-level 3/4 angle",
        "details": "hands washing vegetables under running water, water flowing from faucet, fresh produce nearby",
    },
    {
        "name": "Scandinavian jasna",
        "countertop": "white or light oak",
        "perspective": "Eye-level front view",
        "details": "minimalist bright kitchen, lots of natural light, white tiles, simple ceramic vase, clean lines",
    },
]


# --- Element exclusion block for composites ---
_ELEMENT_EXCLUSION_MAP = {
    "dozownik": "soap dispenser",
    "bateria": "faucet",
    "syfon": "siphon/drain assembly",
    "ociekacz": "draining board",
    "deska do krojenia": "cutting board",
    "koszyk": "basket/colander",
}


def _build_exclusion_block(excluded_elements: list[str] | None) -> str:
    """Buduje blok NEGATIVE dla elementow wykluczonych z kompozytu."""
    if not excluded_elements:
        return ""
    translated = []
    for el in excluded_elements:
        el_lower = el.lower().strip()
        for pl_key, en_val in _ELEMENT_EXCLUSION_MAP.items():
            if pl_key in el_lower:
                translated.append(en_val)
                break
        else:
            translated.append(el)
    if not translated:
        return ""
    items = ", ".join(translated)
    return (
        f"\nCRITICAL EXCLUSION: Do NOT add, generate, or include: {items}. "
        f"These elements are NOT part of this product set. "
        f"If you add any of them, the image will be rejected."
    )


def get_composite_packshot_prompt(
    products: list[dict],
    perspective: str = "top-down",
    thinking_level: str | None = "HIGH",
    excluded_elements: list[str] | None = None,
    style_lock_id: str | None = None,
) -> str:
    """Prompt do kompozytu zestawu (Gemini 3.1 Flash Image, do 10 ref images).

    Args:
        products: lista dict z name i description per produkt
            np. [{"name": "zlew granitowy czarny", "description": "80x50cm, 1 komora"},
                 {"name": "bateria kuchenna czarno-zlota", "description": "wyciagana wylewka"}]
        perspective: "top-down" | "front" | "three-quarter"
        thinking_level: "HIGH" | "MINIMAL" | None (batch)
        excluded_elements: lista elementow do wykluczenia z kompozytu (z NOT_present DNA)
    """
    perspective_map = {
        "top-down": "top-down (bird's eye) view, looking straight down",
        "front": "front (eye-level) view, straight-on perspective",
        "three-quarter": "three-quarter (45 degree) angle view",
    }
    perspective_desc = perspective_map.get(perspective, perspective_map["top-down"])

    # Nazewnictwo obrazów referencyjnych (Nano Banana best practice)
    ref_lines = []
    for i, prod in enumerate(products, 1):
        ref_lines.append(f"Image {i} ({prod['name']}): {prod.get('description', '')}")
    ref_block = "\n".join(ref_lines)

    using_clause = " and ".join(
        f"Image {i} ({p['name']})" for i, p in enumerate(products, 1)
    )

    excluded = [e.lower().strip() for e in (excluded_elements or [])]
    has_faucet = any(
        any(k in f"{p.get('name', '')} {p.get('description', '')}".lower() for k in ("bateria", "faucet", "tap"))
        for p in products
    )
    faucet_excluded = any("bateria" in e or "faucet" in e or "tap" in e for e in excluded)
    if has_faucet and not faucet_excluded:
        faucet_rule = (
            "If a faucet is part of the references, place it naturally and realistically in relation "
            "to the sink and mounting holes."
        )
    else:
        faucet_rule = "Do NOT add any faucet unless it is explicitly present in the reference images."
    style_lock_block = get_style_lock_block(style_lock_id)

    return f"""BACKGROUND LOCK (NON-NEGOTIABLE):
The background must be uniform pure white #FFFFFF (RGB 255,255,255).
No gray cast, no gradient, no texture, no countertop visibility.
Only a subtle natural contact shadow directly under objects is allowed.

CAMERA: Canon EOS R5, 100mm macro lens, f/8, ISO 100.
LIGHTING: 3-point softbox setup, 45-degree key light, fill light from opposite side,
backlight for edge separation. Even illumination, no harsh shadows on product surface.
Output: 2000x2000px (1:1 square). 8K UHD quality.

=== REFERENCE IMAGES ===
{ref_block}

TASK: Using {using_clause}, compose a professional e-commerce product set photograph.
Show ONLY the items from reference images together in {perspective_desc}.
This is a product packshot for Allegro marketplace, NOT a lifestyle photo.

OBJECT SCOPE LOCK (NON-NEGOTIABLE):
Render exactly the objects present in the provided references and product list.
If an object is not explicitly listed, do not generate it.

COMPOSITION:
{faucet_rule}
Accessories positioned exactly as they would be installed in real life.
Product must fill 70-85% of the frame. Center the composition.

{style_lock_block}

{PRESERVATION_LIST_BLOCK}

{MATERIAL_ACCURACY_BLOCK}

NEGATIVE: Do NOT add items not present in reference images. Do NOT alter,
stylize, or reinterpret any product feature. Do NOT add any text, labels,
watermarks, or annotations. Do NOT add extra sink, extra faucet, soap dispenser,
random kitchen props, decorative elements, or additional accessories.
FORBIDDEN OBJECTS: {", ".join(excluded) if excluded else "none"}.
{_build_exclusion_block(excluded_elements)}
{BANNED_PHRASES_BLOCK}"""


def get_product_dna_prompt() -> str:
    """Prompt do analizy produktu ze zdjęcia. Gemini TEXT opisuje dokładnie co widzi."""
    return """You are a product photography analyst for a granite kitchen sink e-commerce store.

Analyze the product image(s) provided. Describe EXACTLY what you see. Do NOT guess, infer, or add elements that are not visible.

Return a JSON object with the following fields (use Polish for all string values):

{
  "product_type": "type of product, e.g. zlew granitowy nablatowy, bateria kuchenna, zestaw zlew + bateria",
  "shape": "overall shape, e.g. kwadratowy, prostokątny z ociekaczem, okrągły",
  "color": "dominant color, e.g. biały, czarny nakrapiany, szary",
  "mounting_type": "nablatowy, wpuszczany, podwieszany, or null if not determinable",
  "has_drainboard": true/false,
  "has_faucet_hole": true/false,
  "bowl_count": 1 or 2,
  "bowl_shape": "kwadratowa, prostokątna, or okrągła",
  "drain_position": "środek, prawy, or lewy",
  "drain_type": "kwadratowy, okrągły, or automatyczny",
  "visible_elements": ["list of ALL elements visible in the image, e.g. zlew, korek kwadratowy chromowany"],
  "NOT_present": ["list of elements that are NOT in the image, e.g. bateria, dozownik, ociekacz"],
  "material_texture": "texture description, e.g. gładki ceramiczny, nakrapiany granitowy, matowy",
  "approximate_dimensions": "estimated size, e.g. ~50x40cm, ~80x50cm",
  "distinctive_features": ["unique traits, e.g. widoczny front (farmhouse), zaokrąglone narożniki"]
}

RULES:
- Respond with ONLY the JSON object. No extra text, no markdown code blocks, no explanation.
- If a field cannot be determined from the image, use null.
- Be precise about what IS and what IS NOT in the image. This is critical for downstream generation.
- visible_elements: list EVERY distinct physical element you can see.
- NOT_present: list common kitchen sink accessories that are ABSENT (bateria, dozownik, ociekacz, syfon, deska do krojenia, koszyk, etc.)."""


def get_lifestyle_prompt_v2(
    scene_config: dict,
    product_dna_json: str,
    corrections: str = "",
    model_type: str = "gemini",
    style_lock_id: str | None = None,
) -> str:
    """Prompt lifestyle v4.3 z DSLR realism, Product DNA, Shadow/Reflection.

    Args:
        scene_config: slownik z name, countertop, perspective, details
        product_dna_json: string JSON z get_product_dna_prompt (Product DNA)
        corrections: string z self-check (puste = pierwsza proba)
        model_type: "gemini" | "lora" | "flux" | "gpt" (dostosowuje prompt)
    """
    no_text = "Do NOT add any text, labels, watermarks, or annotations to the image."
    negative = (
        "NEVER: text overlays, watermarks, plastic sheen on granite, blurry edges, "
        "floating objects, AI artifacts, distorted proportions, extra faucets, extra sinks, "
        "soap dispensers, random props, fake accessories, duplicated objects."
    )

    # Parsuj Product DNA
    try:
        dna = json.loads(product_dna_json)
    except (json.JSONDecodeError, TypeError):
        dna = {}

    visible_str, not_present_str, _ = resolve_scene_elements(
        dna, allow_auto_suggestions=False
    )

    # Product DNA enforcement
    dna_enforcement = build_product_dna_enforcement(
        dna, allow_auto_suggestions=False
    ) if dna else ""
    style_lock_block = get_style_lock_block(style_lock_id)

    corrections_block = ""
    if corrections:
        corrections_block = (
            f"\n\nPREVIOUS ATTEMPT FAILED CHECK. Issues found:\n{corrections}\n"
            f"Fix these specific issues in this generation attempt."
        )

    # LoRA: krotszy prompt z trigger word
    if model_type == "lora":
        from config import LORA_TRIGGER_WORD
        _mounting = (dna.get("mounting_type") or "wpuszczany").lower().strip()
        if _mounting in ("nablatowy", "vessel", "sit-on"):
            _install_lora = "sitting on top of"
            _install_desc = "Full body visible above counter."
        elif _mounting in ("podwieszany", "undermount"):
            _install_lora = "UNDERMOUNT installed below"
            _install_desc = "Mounted below countertop surface. No rim visible from above, only bowl through cutout."
        else:
            _install_lora = "DROP-IN flush-mounted into a cutout in"
            _install_desc = "Bottom mounting part completely hidden below counter surface. Only top rim, bowl, and drainboard visible."
        return f"""{LORA_TRIGGER_WORD} granite sink in {dna.get('color', 'dark')} {_install_lora} \
{scene_config.get('countertop', 'wooden')} countertop. \
{_install_desc} \
{scene_config.get('perspective', 'eye-level')}. \
{scene_config.get('details', 'kitchen accessories')}. \
{DSLR_REALISM_BLOCK} {MATERIAL_ACCURACY_BLOCK} \
{dna_enforcement}
{style_lock_block}
{SHADOW_REFLECTION_BLOCK} {BANNED_PHRASES_BLOCK} {negative} {no_text}{corrections_block}"""

    # Flux: structured 5-step prompt
    if model_type == "flux":
        return f"""Step 1 (ANALYZE): Product DNA: {product_dna_json}
Step 2 (STRUCTURE): Scene composition: {scene_config.get('perspective', 'eye-level')}, \
{scene_config.get('countertop', 'wooden')} countertop, {scene_config.get('details', 'kitchen accessories')}.
Step 3 (CINEMATOGRAPHY): Canon EOS R5, 85mm f/1.4, natural daylight 5500K.
Step 4 (RENDER): Generate photorealistic kitchen scene with product installed in countertop.
{dna_enforcement}
Step 5 (VERIFY): {PRESERVATION_LIST_BLOCK}
{MATERIAL_ACCURACY_BLOCK}
{style_lock_block}
{SHADOW_REFLECTION_BLOCK}
{BANNED_PHRASES_BLOCK}
{negative}
{no_text}{corrections_block}"""

    # GPT Image: input_fidelity hint
    if model_type == "gpt":
        gpt_hint = "Use input_fidelity: high. Preserve every detail from reference."
    else:
        gpt_hint = ""

    # Gemini (default): pelny prompt z DSLR + DNA + Shadow + Thinking mode
    return f"""You are generating a lifestyle kitchen photograph for an e-commerce Allegro listing.
Output: 2000x1500px (4:3 landscape). 8K UHD quality anchor.

The transparent PNG of the real product is provided as input. You MUST use it as the exact reference.
{gpt_hint}

=== PRODUCT DNA (from analysis of the original product) ===
{product_dna_json}

=== FIDELITY RULES (CRITICAL) ===
The product shape, color, mounting type, drain position, bowl count, and bowl shape MUST match EXACTLY what is described in the Product DNA above.
MUST include EXACTLY these elements: {visible_str}
Do NOT add: {not_present_str}
Do NOT invent, add, remove, or alter ANY part of the product.
{PRESERVATION_LIST_BLOCK}

=== OBJECT SCOPE LOCK ===
MUST include ONLY: {visible_str}
MUST NOT include: {not_present_str}
Do not invent any accessory, attachment, or decorative object not listed above.
If an excluded object appears, the image is invalid.

=== SCENE ===
Scene: {scene_config.get('name', 'kitchen lifestyle')}
Countertop: {scene_config.get('countertop', 'wooden')}
Perspective: {scene_config.get('perspective', 'top-down overhead view')}
Props/details: {scene_config.get('details', 'minimal kitchen accessories')}

=== SINK INSTALLATION (CRITICAL - read Product DNA mounting_type) ===
{dna_enforcement}

=== CAMERA & LIGHTING ===
{DSLR_REALISM_BLOCK}

=== MATERIAL ===
{MATERIAL_ACCURACY_BLOCK}

=== STYLE LOCK ===
{style_lock_block}

=== SHADOW & REFLECTION ===
{SHADOW_REFLECTION_BLOCK}

=== NEGATIVE ===
{negative}
{BANNED_PHRASES_BLOCK}
{no_text}{corrections_block}"""


def get_selfcheck_prompt(product_dna_json: str) -> str:
    """Prompt do self-check v4.3: porównanie z ORYGINAŁEM (nie z promptem).

    Oczekuje 2 obrazów: [oryginał, wygenerowane].
    Weighted scoring: bowl_count 25%, color 30%, shape 15%, accessories 10%, realism 20%.
    Próg akceptacji: 8/10.
    """
    # Dynamiczne pytanie #9 na podstawie mounting_type z DNA
    try:
        _dna = json.loads(product_dna_json) if product_dna_json else {}
    except (json.JSONDecodeError, TypeError):
        _dna = {}
    _mount = (_dna.get("mounting_type") or "wpuszczany").lower().strip()

    if _mount in ("nablatowy", "vessel", "sit-on"):
        q9 = (
            "9. Is the sink correctly shown as a VESSEL/SIT-ON type, sitting ON TOP of the countertop? "
            "The full body should be visible above the counter surface. If the sink is incorrectly "
            "recessed into the counter, this is a CRITICAL failure (-3 points from realism_score)."
        )
    elif _mount in ("podwieszany", "undermount"):
        q9 = (
            "9. Is the sink correctly shown as UNDERMOUNT, mounted BELOW the countertop? "
            "The countertop edge should be visible around the opening with NO rim. "
            "If the sink rim is visible on top, this is a CRITICAL failure (-3 points from realism_score)."
        )
    else:
        q9 = (
            "9. Is the sink properly RECESSED into the countertop cutout (drop-in installation)? "
            "The bottom mounting part (trapezoid shape) should be HIDDEN below the counter. "
            "If the sink appears to sit ON TOP of the counter like a box, "
            "this is a CRITICAL failure (-3 points from realism_score)."
        )

    return f"""You are a quality control inspector for e-commerce product photography on Allegro.

You will receive TWO images:
1. FIRST image: the ORIGINAL product photo (reference, ground truth)
2. SECOND image: the AI-GENERATED lifestyle photo that should contain the same product

Your job: compare the product in the GENERATED image against the ORIGINAL and score fidelity.
Compare with the ORIGINAL IMAGE, not just the text description.

=== PRODUCT DNA (expected product attributes) ===
{product_dna_json}

=== SPECIFIC QUESTIONS (answer each before scoring) ===
1. How many bowls are visible in the generated image? Does it match the original?
2. What color is the product? Does it match the original color and speckle pattern?
3. What shape is the product? (rectangular, square, with/without drainboard)
4. Is the drainboard present/absent consistent with the original?
5. Where is the faucet hole? Is it consistent with the original?
6. Are there ANY elements added that are NOT in the original? (faucet, dispenser, accessories)
7. Are there ANY elements MISSING that ARE in the original?
8. Does the product look realistically installed or pasted/floating (sticker effect)?
{q9}

=== SCORING CRITERIA (weighted) ===
Score each dimension 1-10:

- bowl_count_score (25%): Correct number of bowls? Correct shape of bowls?
- color_score (30%): Base color match? Speckle/texture pattern? Finish type (matte/gloss)?
- shape_score (15%): Overall product shape? Drainboard presence? Proportions?
- accessories_score (10%): No added elements? No missing elements? Correct hardware?
- realism_score (20%): Natural integration in scene? Shadows? Reflections? Not floating/pasted?
- overall_score: Weighted average = bowl_count*0.25 + color*0.30 + shape*0.15 + accessories*0.10 + realism*0.20

=== ACCEPTANCE THRESHOLD ===
- overall_score >= 8: ACCEPT (good enough for Allegro listing)
- overall_score 5-7: RETRY with corrections (auto-retry, max 2 attempts)
- overall_score < 5: FALLBACK to next model in chain

=== OUTPUT FORMAT ===
Return ONLY a JSON object. No extra text, no markdown code blocks:

{{
  "bowl_count_score": <1-10>,
  "color_score": <1-10>,
  "shape_score": <1-10>,
  "accessories_score": <1-10>,
  "realism_score": <1-10>,
  "overall_score": <1-10>,
  "answers": ["answer to each of the 9 questions above, in order"],
  "differences": ["lista konkretnych roznic po polsku, np. dodano dozownik ktorego nie ma w oryginale"],
  "corrections_needed": "English instructions for retry, e.g. Remove the soap dispenser. Make the bowl square not rectangular."
}}

If the generated image is perfect (overall_score >= 9), set corrections_needed to empty string "".
Be strict and precise. Score 8 = minor imperfections acceptable. Score 5-7 = noticeable errors. Below 5 = product is wrong."""


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

    # FIX-10/11/12: Test propagacji kolorów
    from catalogs import get_kolory_per_element
    kpe = get_kolory_per_element("granitowe_zlewy")
    assert "Szary" in kpe["kolor_syfon_widoczny"], "Brak Szary w syfonie"
    assert "Szara" in kpe["kolor_bateria"], "Brak Szara w baterii"
    assert "Stalowa" in kpe["kolor_bateria"], "Brak Stalowa w baterii"
    print("FIX-10/11: nowe kolory: OK")

    # FIX-12: beech w lifestyle
    z, l = get_image_prompts("Zestaw (zlew + bateria + syfon)", catalog_name="granitowe_zlewy")
    beech_count = sum(1 for p in l if "beech" in p["prompt"])
    assert beech_count >= 3, f"beech w {beech_count}/3 promptach drewnianych"
    print(f"FIX-12: beech w lifestyle: OK ({beech_count} promptów)")

    # FIX-08: sanityzacja regen
    regen_test = get_regen_prompt("edit", "<script>alert('xss')</script>" + "a" * 600, "test")
    assert "<script>" not in regen_test, "XSS w regen prompt"
    assert len(regen_test) < 2000, "Prompt za długi po sanityzacji"
    print("FIX-08: sanityzacja regen: OK")

    # --- Pipeline v4.3: Product DNA + Lifestyle v2 + Self-check + Composite ---

    # 9. Test get_product_dna_prompt
    dna_prompt = get_product_dna_prompt()
    assert "product_type" in dna_prompt, "Brak product_type w DNA prompt"
    assert "visible_elements" in dna_prompt, "Brak visible_elements w DNA prompt"
    assert "NOT_present" in dna_prompt, "Brak NOT_present w DNA prompt"
    assert "ONLY the JSON" in dna_prompt, "Brak instrukcji JSON-only"
    print("get_product_dna_prompt: OK")

    # 10. Test LIFESTYLE_SCENES (6 scen)
    assert len(LIFESTYLE_SCENES) == 6, f"Oczekiwano 6 scen, jest {len(LIFESTYLE_SCENES)}"
    scene_names = [s["name"] for s in LIFESTYLE_SCENES]
    assert "Drewno · overhead" in scene_names, "Brak sceny Drewno · overhead"
    assert "Granit · close-up" in scene_names, "Brak sceny Granit · close-up"
    assert "W uzyciu" in scene_names, "Brak sceny W uzyciu"
    assert "Scandinavian jasna" in scene_names, "Brak sceny Scandinavian jasna"
    for scene in LIFESTYLE_SCENES:
        assert "countertop" in scene, f"Brak countertop w scenie {scene['name']}"
        assert "perspective" in scene, f"Brak perspective w scenie {scene['name']}"
        assert "details" in scene, f"Brak details w scenie {scene['name']}"
    print(f"LIFESTYLE_SCENES: OK ({len(LIFESTYLE_SCENES)} scen)")

    # 11. Test get_lifestyle_prompt_v2 (Gemini, default)
    test_dna = json.dumps({
        "product_type": "zlew granitowy nablatowy",
        "shape": "prostokątny z ociekaczem",
        "color": "czarny nakrapiany",
        "mounting_type": "wpuszczany",
        "has_drainboard": True,
        "has_faucet_hole": True,
        "bowl_count": 1,
        "bowl_shape": "kwadratowa",
        "drain_position": "środek",
        "drain_type": "kwadratowy",
        "visible_elements": ["zlew", "ociekacz", "korek kwadratowy chromowany"],
        "NOT_present": ["bateria", "dozownik"],
        "material_texture": "nakrapiany granitowy",
        "approximate_dimensions": "~80x50cm",
        "distinctive_features": ["zaokrąglone narożniki"]
    }, ensure_ascii=False)

    lp_v2 = get_lifestyle_prompt_v2(LIFESTYLE_SCENES[0], test_dna)
    assert "zlew" in lp_v2, "Brak Product DNA w lifestyle prompt"
    assert "Do NOT add" in lp_v2, "Brak negative list w lifestyle prompt"
    assert "MUST include EXACTLY" in lp_v2, "Brak positive list w lifestyle prompt"
    assert "FIDELITY RULES" in lp_v2, "Brak fidelity rules"
    assert "STYLE LOCK" in lp_v2, "Brak STYLE LOCK block"
    assert "DSLR" in lp_v2 or "Canon EOS R5" in lp_v2, "Brak DSLR realism block"
    assert "SHADOW" in lp_v2, "Brak Shadow/Reflection block"
    assert "PRESERVATION" in lp_v2, "Brak Preservation block"
    assert "2000x1500" in lp_v2, "Brak rozdzielczosci 2000x1500"
    assert "PREVIOUS ATTEMPT" not in lp_v2, "Corrections block nie powinien byc bez corrections"
    print("get_lifestyle_prompt_v2 (gemini, bez korekcji): OK")

    # 12. Test get_lifestyle_prompt_v2 z corrections
    lp_v2_corr = get_lifestyle_prompt_v2(
        LIFESTYLE_SCENES[2], test_dna,
        corrections="Remove the soap dispenser. Make the bowl square."
    )
    assert "PREVIOUS ATTEMPT FAILED CHECK" in lp_v2_corr, "Brak corrections block"
    assert "Remove the soap dispenser" in lp_v2_corr, "Brak tresci korekcji"
    assert "granite (NOT marble)" in lp_v2_corr, "Brak countertop ze scene_config"
    print("get_lifestyle_prompt_v2 (z korekcja): OK")

    # 13. Test get_lifestyle_prompt_v2 z niepoprawnym JSON
    lp_v2_bad = get_lifestyle_prompt_v2(LIFESTYLE_SCENES[0], "niepoprawny json")
    assert "MUST include EXACTLY" in lp_v2_bad, "Prompt powinien dzialac mimo zlego JSON"
    print("get_lifestyle_prompt_v2 (zly JSON): OK")

    # 14. Test get_lifestyle_prompt_v2 model_type=flux
    lp_flux = get_lifestyle_prompt_v2(LIFESTYLE_SCENES[0], test_dna, model_type="flux")
    assert "Step 1" in lp_flux, "Flux: brak structured 5-step"
    assert "Step 5" in lp_flux, "Flux: brak Step 5"
    print("get_lifestyle_prompt_v2 (flux): OK")

    # 15. Test get_selfcheck_prompt (v4.3 z nowymi wagami)
    sc_prompt = get_selfcheck_prompt(test_dna)
    assert "bowl_count_score" in sc_prompt, "Brak bowl_count_score w selfcheck"
    assert "color_score" in sc_prompt, "Brak color_score w selfcheck"
    assert "shape_score" in sc_prompt, "Brak shape_score w selfcheck"
    assert "accessories_score" in sc_prompt, "Brak accessories_score w selfcheck"
    assert "realism_score" in sc_prompt, "Brak realism_score w selfcheck"
    assert "overall_score" in sc_prompt, "Brak overall_score w selfcheck"
    assert "25%" in sc_prompt, "Brak wagi 25% bowl_count"
    assert "30%" in sc_prompt, "Brak wagi 30% color"
    assert ">= 8" in sc_prompt, "Brak progu akceptacji 8"
    assert "differences" in sc_prompt, "Brak differences w selfcheck"
    assert "corrections_needed" in sc_prompt, "Brak corrections_needed w selfcheck"
    assert "PRODUCT DNA" in sc_prompt, "Brak Product DNA w selfcheck"
    assert "TWO images" in sc_prompt, "Brak instrukcji o 2 obrazach"
    assert "ONLY a JSON" in sc_prompt, "Brak instrukcji JSON-only"
    print("get_selfcheck_prompt (v4.3): OK")

    # 16. Test get_composite_packshot_prompt
    products = [
        {"name": "zlew granitowy czarny", "description": "80x50cm, 1 komora"},
        {"name": "bateria czarno-zlota", "description": "wyciagana wylewka"},
    ]
    comp_prompt = get_composite_packshot_prompt(products, "top-down")
    assert "Image 1 (zlew granitowy czarny)" in comp_prompt, "Brak nazwy Image 1"
    assert "Image 2 (bateria czarno-zlota)" in comp_prompt, "Brak nazwy Image 2"
    assert "2000x2000" in comp_prompt, "Brak rozdzielczosci 2000x2000"
    assert "#FFFFFF" in comp_prompt, "Brak bialego tla #FFFFFF"
    assert "BACKGROUND LOCK" in comp_prompt, "Brak BACKGROUND LOCK"
    assert "OBJECT SCOPE LOCK" in comp_prompt, "Brak OBJECT SCOPE LOCK"
    assert "STYLE LOCK" in comp_prompt, "Brak STYLE LOCK"
    assert "Canon EOS R5" in comp_prompt, "Brak Canon EOS R5"
    assert "bird's eye" in comp_prompt, "Brak perspektywy top-down"
    print("get_composite_packshot_prompt: OK")

    # 17. Test get_composite_packshot_prompt (three-quarter)
    comp_34 = get_composite_packshot_prompt(products, "three-quarter")
    assert "45 degree" in comp_34, "Brak perspektywy three-quarter"
    print("get_composite_packshot_prompt (three-quarter): OK")

    # 17b. Test excluded_elements w composite prompt
    comp_excl = get_composite_packshot_prompt(
        products, excluded_elements=["dozownik", "deska do krojenia"]
    )
    assert "soap dispenser" in comp_excl, "Brak soap dispenser w exclusion block"
    assert "cutting board" in comp_excl, "Brak cutting board w exclusion block"
    assert "CRITICAL EXCLUSION" in comp_excl, "Brak CRITICAL EXCLUSION"
    comp_no_excl = get_composite_packshot_prompt(products, excluded_elements=[])
    assert "CRITICAL EXCLUSION" not in comp_no_excl, "Puste excluded nie powinno generowac bloku"
    print("get_composite_packshot_prompt (excluded_elements): OK")

    # 18. Test blokow stalych
    assert "Canon EOS R5" in DSLR_REALISM_BLOCK, "DSLR block brak Canon"
    assert "5500K" in DSLR_REALISM_BLOCK, "DSLR block brak 5500K"
    assert "sticker" in SHADOW_REFLECTION_BLOCK, "Shadow block brak sticker"
    assert "moody" in BANNED_PHRASES_BLOCK, "Banned block brak moody"
    assert "PRESERVATION" in PRESERVATION_LIST_BLOCK, "Preservation block brak"
    print("Bloki stałe v4.3: OK")

    # 19. Test build_product_dna_enforcement
    test_dna_dict = json.loads(test_dna)
    enforcement = build_product_dna_enforcement(test_dna_dict)
    assert "EXACTLY 1 bowl" in enforcement, "Enforcement: brak bowl_count"
    assert "WITH drainboard" in enforcement, "Enforcement: brak drainboard"
    assert "WITH faucet hole" in enforcement, "Enforcement: brak faucet hole"
    assert "czarny nakrapiany" in enforcement, "Enforcement: brak koloru"
    print("build_product_dna_enforcement: OK")

    # 20. Test resolve_scene_elements: auto-suggest baterii
    vis, exc, auto = resolve_scene_elements({
        "visible_elements": ["zlew", "ociekacz"],
        "NOT_present": ["bateria", "dozownik", "deska do krojenia"],
        "color": "czarny nakrapiany",
    })
    assert "faucet" in vis, f"Auto-suggested bateria powinna byc w visible_str: {vis}"
    assert "bateria" not in exc, f"Bateria NIE powinna byc w exclude_str: {exc}"
    assert "dozownik" in exc, f"Dozownik powinien byc w exclude_str: {exc}"
    assert len(auto) == 1, f"Oczekiwano 1 auto-suggested, jest {len(auto)}"
    print("resolve_scene_elements (auto-suggest baterii): OK")

    vis_gen, exc_gen, auto_gen = resolve_scene_elements({
        "visible_elements": ["zlew", "ociekacz"],
        "NOT_present": ["bateria", "dozownik"],
    }, allow_auto_suggestions=False)
    assert "faucet" not in vis_gen, f"Tryb generacji: brak auto-suggest baterii: {vis_gen}"
    assert "bateria" in exc_gen, f"Tryb generacji: bateria ma byc w exclude: {exc_gen}"
    assert len(auto_gen) == 0, f"Tryb generacji: auto-suggest powinien byc pusty: {auto_gen}"
    print("resolve_scene_elements (generation mode, no auto): OK")

    # 21. Test resolve_scene_elements: bateria present = brak auto-suggest
    vis2, exc2, auto2 = resolve_scene_elements({
        "visible_elements": ["zlew", "bateria chromowana"],
        "NOT_present": ["dozownik"],
        "color": "czarny",
    })
    assert len(auto2) == 0, f"Nie powinno byc auto-suggest gdy bateria present: {auto2}"
    assert "bateria chromowana" in vis2, f"Bateria powinna byc w visible: {vis2}"
    print("resolve_scene_elements (bateria present): OK")

    # 22. Test resolve_scene_elements: puste dane
    vis3, exc3, auto3 = resolve_scene_elements({})
    assert vis3 == "all elements from reference", f"Puste dane: visible powinno byc default: {vis3}"
    assert exc3 == "nothing extra", f"Puste dane: exclude powinno byc default: {exc3}"
    assert len(auto3) == 0, f"Puste dane: brak auto-suggest: {auto3}"
    print("resolve_scene_elements (puste dane): OK")

    # 23. Test enforcement bez auto-suggest (default)
    test_dna_no_faucet = {
        **test_dna_dict,
        "visible_elements": ["zlew"],
        "NOT_present": ["bateria", "dozownik"],
    }
    enf2 = build_product_dna_enforcement(test_dna_no_faucet)
    assert "color-matched kitchen faucet" not in enf2, f"Default generacji: brak auto-suggest baterii: {enf2[:200]}"
    assert "ZERO NOT_present:" in enf2 and "bateria" in enf2 and "dozownik" in enf2, f"Dozownik/bateria w ZERO: {enf2[:300]}"
    enf3 = build_product_dna_enforcement(test_dna_no_faucet, allow_auto_suggestions=True)
    assert "faucet" in enf3, f"Tryb UI: powinien zawierac auto-suggested baterie: {enf3[:200]}"
    print("build_product_dna_enforcement (no-auto + optional auto): OK")

    # 24. Test sanityzacja: element w visible I NOT_present jednoczesnie
    vis_san, exc_san, auto_san = resolve_scene_elements({
        "visible_elements": ["zlew", "bateria chromowana"],
        "NOT_present": ["bateria", "dozownik"],
        "color": "czarny",
    })
    assert len(auto_san) == 0, f"Sanityzacja: bateria w visible = brak auto-suggest: {auto_san}"
    assert "bateria" not in exc_san, f"Sanityzacja: bateria w visible nie powinna byc w exclude: {exc_san}"
    assert "dozownik" in exc_san, f"Sanityzacja: dozownik powinien pozostac: {exc_san}"
    print("resolve_scene_elements (sanityzacja visible vs NOT_present): OK")

    print(f"\nALL TESTS PASSED ({26} tests)")
