"""
Integracja z BaseLinker API.

Obsluguje wysylke produktow, konwersje obrazow i auto-kategoryzacje.
"""

import io
import json
import time
import base64
import requests

try:
    import PIL.Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from catalogs import get_bl_category_id

BL_API_URL = "https://api.baselinker.com/connector.php"


def bl_request(method, parameters, token, max_retries=2):
    """Wykonaj request do BaseLinker API z retry."""
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
                raise Exception("BL: Pusta odpowiedz (za duzy request? sprawdz rozmiar obrazow)")
            result = response.json()
            if result.get("status") == "ERROR":
                raise Exception(f"BL: {result.get('error_code')} · {result.get('error_message')}")
            return result
        except (requests.Timeout, requests.ConnectionError) as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(5 * (attempt + 1))
            else:
                raise
    raise last_error


def check_sku_exists(token, inventory_id, sku):
    """Sprawdza czy produkt z danym SKU juz istnieje w BaseLinker."""
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
    Zmniejsza do max_size px zeby zmiescic sie w limicie 2MB."""
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


def send_to_baselinker(token, inventory_id, price_group_id, warehouse_id,
                        name, description_html, images_dict,
                        price=0, sku="", category_id=0,
                        extra_fields=None, stock=1,
                        ean="", weight=0, height=0, width=0, length=0,
                        catalog_name=None, kategoria=None):
    """Wysyla produkt do BaseLinker przez API.

    Jesli catalog_name i kategoria sa podane, auto-podstawia category_id
    z mapowania w catalogs.py (o ile category_id == 0).
    """
    if category_id == 0 and catalog_name and kategoria:
        category_id = get_bl_category_id(catalog_name, kategoria)

    text_fields = {
        "name": name,
        "description": description_html,
    }
    if extra_fields:
        for field_id, value in extra_fields.items():
            text_fields[f"extra_field_{field_id}"] = str(value)

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
