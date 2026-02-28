"""
GranitoweZlewy · Klient BaseLinker API v3.0
Integracja z Allegro: walidacja produktu, upload zdjęć, photo ordering.
Polskie komunikaty, retry, auto-kategoryzacja.
"""

import asyncio
import base64
import io
import json
import logging
import os
import time
from functools import partial

import requests

try:
    import PIL.Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from catalogs import get_bl_category_id

# ---------------------------------------------------------------------------
# Konfiguracja
# ---------------------------------------------------------------------------

BASELINKER_API_TOKEN = os.environ.get("BASELINKER_API_TOKEN", "")

logger = logging.getLogger("baselinker")

BL_API_URL = "https://api.baselinker.com/connector.php"

# Kolejność zdjęć na Allegro (krytyczna dla konwersji)
ALLEGRO_PHOTO_ORDER = [
    "hero_packshot",          # #1: Zestaw na białym tle, 1:1, 2000x2000
    "packshot_zlew",          # #2: Sam zlew
    "packshot_bateria",       # #3: Sama bateria (jeśli w zestawie)
    "lifestyle_scandinavian", # #4: Jasna kuchnia (najlepsza miniatura)
    "lifestyle_drewno",       # #5: Blat dąb/orzech
    "lifestyle_granit",       # #6: Blat granitowy
    "lifestyle_w_uzyciu",     # #7: Produkt w użyciu
    "lifestyle_frontal",      # #8: Widok frontalny
]

REQUIRED_FIELDS = ["title", "description_html", "price", "images"]
MAX_TITLE_LENGTH = 75
MIN_TITLE_LENGTH = 60

BL_ERROR_MESSAGES_PL = {
    "ERROR_EMPTY_API_TOKEN": "Brak tokenu API. Ustaw token w Ustawienia > Klucze API w panelu BaseLinker.",
    "ERROR_NO_ACCESS_TO_API": "Brak dostępu do API. Sprawdź uprawnienia tokenu w panelu BaseLinker.",
    "ERROR_WRONG_API_TOKEN": "Nieprawidłowy token API. Skopiuj ponownie token z panelu BaseLinker.",
    "ERROR_NO_ACCESS_TO_METHOD": "Brak uprawnień do tej metody. Sprawdź zakres tokenu API.",
    "ERROR_UNKNOWN_METHOD": "Nieznana metoda API. Sprawdź nazwę metody.",
    "ERROR_TOO_MANY_REQUESTS": "Zbyt wiele zapytań. Odczekaj chwilę i spróbuj ponownie.",
}


# ---------------------------------------------------------------------------
# Pomocnicze (zachowane z v2)
# ---------------------------------------------------------------------------

def _translate_bl_error(error_code: str, error_message: str) -> str:
    """Tłumaczy kody błędów BaseLinker na komunikaty polskie."""
    pl_msg = BL_ERROR_MESSAGES_PL.get(error_code)
    if pl_msg:
        return f"{pl_msg} (Kod: {error_code})"
    return f"Błąd BaseLinker: {error_message} (Kod: {error_code})"


def bl_request(method, parameters, token, max_retries=2):
    """Synchroniczny request do BaseLinker API z retry."""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                BL_API_URL,
                headers={"X-BLToken": token},
                data={
                    "method": method,
                    "parameters": json.dumps(parameters),
                },
                timeout=120,
            )
            if not response.text:
                raise Exception("BL: Pusta odpowiedź (za duży request? sprawdź rozmiar obrazów)")
            result = response.json()
            if result.get("status") == "ERROR":
                raise Exception(_translate_bl_error(
                    result.get("error_code", ""),
                    result.get("error_message", ""),
                ))
            return result
        except requests.Timeout:
            last_error = Exception("Przekroczono czas oczekiwania na odpowiedź BaseLinker. Spróbuj ponownie.")
            if attempt < max_retries:
                time.sleep(5 * (attempt + 1))
            else:
                raise last_error
        except requests.ConnectionError:
            last_error = Exception("Brak połączenia z BaseLinker. Sprawdź internet.")
            if attempt < max_retries:
                time.sleep(5 * (attempt + 1))
            else:
                raise last_error
    raise last_error


def check_sku_exists(token, inventory_id, sku):
    """Sprawdza czy produkt z danym SKU już istnieje w BaseLinker."""
    if not sku:
        return None
    try:
        result = bl_request("getInventoryProductsList", {
            "inventory_id": inventory_id,
            "filter_sku": sku,
        }, token)
        products = result.get("products", {})
        if products:
            first_id = list(products.keys())[0]
            return first_id
    except Exception:
        pass
    return None


def images_to_base64(images_dict, max_size=1200):
    """Konwertuje PIL Images na obiekt base64 dla BaseLinker API.
    Format BL: {"0": "data:...", "1": "data:...", ...} (klucze 0-15).
    Zmniejsza do max_size px żeby zmieścić się w limicie 2MB."""
    result = {}
    for i, (name, img) in enumerate(images_dict.items()):
        if i > 15:
            break
        w, h = img.size
        if max(w, h) > max_size:
            ratio = max_size / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), PIL.Image.LANCZOS)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        result[str(i)] = f"data:{b64}"
    return result


def sort_images_for_allegro(image_paths: list[str]) -> list[str]:
    """Sortuje ścieżki obrazów wg ALLEGRO_PHOTO_ORDER.
    Obrazy pasujące do nazw w liście idą pierwsze (wg kolejności).
    Pozostałe dołączane na końcu w oryginalnej kolejności."""
    order_map = {name: idx for idx, name in enumerate(ALLEGRO_PHOTO_ORDER)}

    def sort_key(path: str) -> tuple[int, int]:
        filename = os.path.splitext(os.path.basename(path))[0].lower()
        for name, idx in order_map.items():
            if name in filename:
                return (0, idx)
        return (1, 0)

    return sorted(image_paths, key=sort_key)


# ---------------------------------------------------------------------------
# Klasa BaseLinkerClient (v3.0, async)
# ---------------------------------------------------------------------------

class BaseLinkerClient:
    """Klient BaseLinker API v3.0. Polskie komunikaty, walidacja, photo ordering."""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = BL_API_URL

    async def _async_call(self, method: str, parameters: dict | None = None) -> dict:
        """Asynchroniczne wywołanie BaseLinker API przez run_in_executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            partial(bl_request, method, parameters or {}, self.api_token),
        )

    async def test_connection(self) -> dict:
        """Test połączenia z BaseLinker. Zwraca status."""
        try:
            await self._async_call("getOrders", {"limit": 1})
            logger.info("Połączenie z BaseLinker: OK")
            return {"status": "SUCCESS", "message": "Połączenie z BaseLinker: OK"}
        except Exception as exc:
            logger.error("Błąd połączenia z BaseLinker: %s", exc)
            return {"status": "ERROR", "message": f"Błąd połączenia z BaseLinker: {exc}"}

    async def upload_images(self, image_paths: list[str]) -> list[str]:
        """Uploaduje obrazy do BaseLinker i zwraca URLe w kolejności Allegro."""
        sorted_paths = sort_images_for_allegro(image_paths)
        uploaded_urls: list[str] = []

        for path in sorted_paths:
            try:
                with open(path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode("utf-8")

                result = await self._async_call("addProductImage", {
                    "image_source": f"data:image/jpeg;base64,{image_data}",
                })
                url = result.get("image_url", "")
                if url:
                    uploaded_urls.append(url)
            except OSError as exc:
                logger.error("Nie można odczytać pliku %s: %s", path, exc)
            except Exception as exc:
                logger.warning("Błąd uploadu obrazu %s: %s", path, exc)

        logger.info("Uploadowano %d zdjęć do BaseLinker", len(uploaded_urls))
        return uploaded_urls

    async def add_product(self, product_data: dict) -> dict:
        """Dodaje produkt do BaseLinker/Allegro."""
        parameters = {
            "storage_id": "bl_1",
            "product_id": "",
            "ean": product_data.get("ean", ""),
            "name": product_data.get("title", ""),
            "description": product_data.get("description_html", ""),
            "price_brutto": product_data.get("price", 0),
            "images": product_data.get("images", []),
        }

        try:
            result = await self._async_call("addProduct", parameters)
            product_id = result.get("product_id", "")
            logger.info("Produkt dodany pomyślnie: %s", product_id)
            return {
                "status": "ok",
                "product_id": product_id,
                "message": f"Produkt dodany pomyślnie: {product_id}",
            }
        except Exception as exc:
            logger.error("Błąd dodawania produktu: %s", exc)
            return {"status": "error", "errors": [f"Błąd dodawania produktu: {exc}"]}

    def validate_product_data(self, data: dict) -> list[str]:
        """Waliduje dane produktu. Zwraca listę błędów (pusta = OK)."""
        errors: list[str] = []

        for field in REQUIRED_FIELDS:
            if not data.get(field):
                errors.append(f"Brak wymaganego pola: {field}")

        title = data.get("title", "")
        if len(title) < MIN_TITLE_LENGTH:
            errors.append(f"Tytuł za krótki ({len(title)} zn., min {MIN_TITLE_LENGTH})")
        if len(title) > MAX_TITLE_LENGTH:
            errors.append(f"Tytuł za długi ({len(title)} zn., max {MAX_TITLE_LENGTH})")

        images = data.get("images", [])
        if len(images) < 3:
            errors.append(f"Za mało zdjęć ({len(images)}, min 3)")

        price = data.get("price", 0)
        if not isinstance(price, (int, float)) or price <= 0:
            errors.append("Cena musi być liczbą większą od 0")

        if errors:
            logger.warning("Walidacja nieudana: %s", "; ".join(errors))

        return errors


# ---------------------------------------------------------------------------
# Funkcja wysyłki (sync, zachowana z v2 dla kompatybilności z poc-aukcje.py)
# ---------------------------------------------------------------------------

def send_to_baselinker_sync(
    token, inventory_id, price_group_id, warehouse_id,
    name, description_html, images_dict,
    price=0, sku="", category_id=0,
    extra_fields=None, stock=1,
    ean="", weight=0, height=0, width=0, length=0,
    catalog_name=None, kategoria=None,
    features=None,
):
    """Wysyła produkt do BaseLinker przez API (sync).
    Jeśli catalog_name i kategoria są podane, auto-podstawia category_id."""
    if category_id == 0 and catalog_name and kategoria:
        category_id = get_bl_category_id(catalog_name, kategoria)

    text_fields = {
        "name": name,
        "description": description_html,
    }
    if extra_fields:
        for field_id, value in extra_fields.items():
            text_fields[f"extra_field_{field_id}"] = str(value)

    if features and isinstance(features, dict):
        text_fields["features"] = {str(k): str(v) for k, v in features.items() if v is not None}

    image_data = images_to_base64(images_dict)

    parameters = {
        "inventory_id": inventory_id,
        "text_fields": text_fields,
        "images": image_data,
        "sku": sku,
        "tax_rate": 23,
    }
    if ean:
        parameters["ean"] = ean
    if weight > 0:
        parameters["weight"] = weight
    if height > 0:
        parameters["height"] = height
    if width > 0:
        parameters["width"] = width
    if length > 0:
        parameters["length"] = length
    if price > 0:
        parameters["prices"] = {str(price_group_id): price}
    if stock > 0:
        parameters["stock"] = {warehouse_id: stock}
    if category_id > 0:
        parameters["category_id"] = category_id

    return bl_request("addInventoryProduct", parameters, token)


# Alias dla kompatybilności wstecznej
send_to_baselinker = send_to_baselinker_sync


# ---------------------------------------------------------------------------
# Funkcja wysyłki (async, v3.0, do użycia z api.py)
# ---------------------------------------------------------------------------

async def send_to_baselinker_async(
    token: str,
    product_data: dict,
    image_paths: list[str],
) -> dict:
    """Wysyła produkt z obrazami do BaseLinker (async). Zwraca wynik."""
    client = BaseLinkerClient(token)

    # Walidacja
    errors = client.validate_product_data(product_data)
    if errors:
        return {"status": "error", "errors": errors}

    # Test połączenia
    conn = await client.test_connection()
    if conn.get("status") != "SUCCESS":
        return {"status": "error", "errors": ["Błąd połączenia z BaseLinker"]}

    # Upload obrazów w kolejności Allegro
    image_urls = await client.upload_images(image_paths)
    if not image_urls:
        return {"status": "error", "errors": ["Nie udało się uploadować żadnego zdjęcia"]}

    product_data["images"] = image_urls

    # Dodaj produkt
    result = await client.add_product(product_data)
    return result
