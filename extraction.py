"""
Auto-ekstrakcja danych ze specyfikacji produktu.

Uzywa Gemini text API do parsowania specyfikacji na ustrukturyzowany JSON.
"""

import json
import logging

from config import MODEL

try:
    from prompts import get_extraction_prompt
except ImportError:
    def get_extraction_prompt(spec_text):
        return f"Extract product data from: {spec_text}. Return JSON."

try:
    from google.genai import types
except ImportError:
    types = None

EXTRACTION_SCHEMA = {
    "waga_kg": None,
    "wysokosc_cm": None,
    "szerokosc_cm": None,
    "dlugosc_cm": None,
    "material": None,
    "kolor": None,
    "kolor_zlew": None,
    "kolor_bateria": None,
    "kolor_syfon_widoczny": None,
    "kolor_dozownik": None,
    "typ_montazu": None,
    "srednica_odplywu": None,
    "min_szafka_cm": None,
    "glebokosc_komory_mm": None,
    "model": None,
    "marka": None,
    "ean": None,
    "kategoria_sugerowana": None,
}


def extract_spec_data(client, spec_text, pil_images=None):
    """Ekstrakcja danych ze specyfikacji produktu przez Gemini.

    Args:
        client: Gemini API client
        spec_text: tekst specyfikacji produktu
        pil_images: opcjonalne zdjecia PIL (do analizy wizualnej)

    Returns:
        dict zgodny z EXTRACTION_SCHEMA. Brak danych = None.
    """
    result = dict(EXTRACTION_SCHEMA)
    if not spec_text or not spec_text.strip():
        return result

    try:
        prompt = get_extraction_prompt(spec_text)
        contents = [prompt]
        if pil_images:
            contents += pil_images[:4]

        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=["TEXT"]) if types else None,
        )

        if not response.parts:
            return result

        raw_text = ""
        for part in response.parts:
            if part.text:
                raw_text += part.text

        # Wyciagnij JSON z odpowiedzi
        raw_text = raw_text.strip()
        if "```" in raw_text:
            parts = raw_text.split("```")
            for p in parts:
                p = p.strip()
                if p.startswith("json"):
                    p = p[4:].strip()
                if p.startswith("{"):
                    raw_text = p
                    break

        parsed = json.loads(raw_text)

        # Walidacja zakresow
        for key, value in parsed.items():
            if key not in EXTRACTION_SCHEMA:
                continue
            if value is None:
                result[key] = None
                continue
            # Walidacja numeryczna
            if key == "waga_kg" and isinstance(value, (int, float)):
                result[key] = value if 0 < value < 100 else None
            elif key in ("wysokosc_cm", "szerokosc_cm", "dlugosc_cm") and isinstance(value, (int, float)):
                result[key] = value if 0 < value < 300 else None
            elif key in ("min_szafka_cm",) and isinstance(value, (int, float)):
                result[key] = value if 0 < value < 200 else None
            elif key in ("glebokosc_komory_mm",) and isinstance(value, (int, float)):
                result[key] = value if 0 < value < 500 else None
            else:
                result[key] = value

    except json.JSONDecodeError:
        logging.warning("Ekstrakcja: Gemini nie zwrócił prawidłowego JSON")
    except Exception as e:
        logging.warning(f"Ekstrakcja specyfikacji: {type(e).__name__}: {e}")

    # Auto-default marka
    if result["marka"] is None:
        result["marka"] = "GranitoweZlewy"

    return result
