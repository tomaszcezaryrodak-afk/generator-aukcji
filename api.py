"""
FastAPI backend: Generator Aukcji Produktowych v4.0
Klient: Granitowe Zlewy (Marcin Mysliwiec)
Stack: FastAPI + Gemini API + BaseLinker API
Migracja z dashboard.py (Streamlit) na REST API + SSE.
"""

import asyncio
import base64
import hmac
import html as html_lib
import io
import json
import os
import re
import shutil
import time
import uuid
import zipfile
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

import bcrypt

from fastapi import FastAPI, Form, Request, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import (
    get_secret, MODEL, OPENAI_API_KEY, OPENAI_IMAGE_MODEL,
    CORS_ORIGINS, MAX_UPLOAD_SIZE_MB, ALLOWED_IMAGE_MAGIC, REMBG_MODEL,
    PHASE_TIMEOUT_SEC, MAX_FEEDBACK_ROUNDS, SOFT_WARNING_ROUNDS,
    MAX_FEEDBACK_LENGTH, MAX_API_CALLS_PER_SESSION as CONFIG_MAX_API_CALLS,
    MAX_CONCURRENT_SESSIONS,
    COST_GEMINI_TEXT_USD, COST_GEMINI_PRO_IMAGE_USD, USD_TO_PLN,
    GEMINI_API_KEY, FAL_AI_API_KEY, APP_PASSWORD,
)
from sessions import (
    SessionData, sessions, create_session, get_session, cleanup_expired,
    check_lockout, record_failed_login, reset_lockout,
    TooManySessions, create_sse_ticket, validate_sse_ticket,
    CLEANUP_INTERVAL,
)

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

try:
    from rembg import remove as rembg_remove, new_session as rembg_new_session
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

# Module-level rembg session (model ladowany raz)
_rembg_session = None

def get_rembg_session():
    global _rembg_session
    if _rembg_session is None and REMBG_AVAILABLE:
        _rembg_session = rembg_new_session(REMBG_MODEL)
    return _rembg_session

try:
    import openai as openai_lib
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

_openai_client = None

def get_openai_client():
    global _openai_client
    if _openai_client is None and OPENAI_AVAILABLE and OPENAI_API_KEY:
        _openai_client = openai_lib.OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client

from catalogs import get_catalog_display_names, get_categories, get_kolor_map, get_kolory_per_element, get_features_for_type
from prompts import (
    get_image_prompts, generate_description_prompt, parse_description_sections,
    get_description_revision_prompt, check_ban_list, get_analysis_prompt,
    get_product_dna_prompt, get_lifestyle_prompt_v2, get_selfcheck_prompt,
    LIFESTYLE_SCENES, get_composite_packshot_prompt,
)
from image_generators import (
    PillowPackshotGenerator, GeminiFlashImageGenerator,
    generate_with_fallback, get_lifestyle_generators, get_composite_generators,
    get_provider_status,
)
from lora_training import LoRATrainer, LoRAConfig, quick_train
from baselinker import send_to_baselinker, check_sku_exists, bl_request
from extraction import extract_spec_data
from history import (
    save_generation, load_history, cleanup_old_outputs,
    save_auction, load_auction, list_auctions, export_all_auctions,
)

try:
    from prompts import get_regen_prompt
    REGEN_AVAILABLE = True
except ImportError:
    REGEN_AVAILABLE = False

# ---------------------------------------------------------------------------
# Stale
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
UPLOADS_DIR = BASE_DIR / "uploads"

COST_PER_IMAGE_USD = COST_GEMINI_PRO_IMAGE_USD  # 0.134 z config.py
COST_PER_TEXT_CALL_EST = COST_GEMINI_TEXT_USD     # 0.02 z config.py

RATE_LIMIT_SEC = float(os.getenv("RATE_LIMIT_SEC", "2"))
MAX_API_CALLS_PER_SESSION = 30
MAX_REGEN_PER_SESSION = 10
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_FILES = 10

ALLOWED_HTML_TAGS = {'h2', 'h3', 'p', 'ul', 'ol', 'li', 'b', 'strong', 'br', 'em', 'small'}

ERROR_MESSAGES_PL = {
    "429": "Zbyt wiele zapytan do API. Odczekaj minute i sprobuj ponownie.",
    "500": "Blad serwera Gemini. Sprobuj ponownie za chwile.",
    "503": "Serwer Gemini tymczasowo niedostepny. Sprobuj za minute.",
    "RESOURCE_EXHAUSTED": "Wyczerpano limit API. Odczekaj kilka minut.",
    "SAFETY": "Gemini zablokowal tresc (filtr bezpieczenstwa). Zmien specyfikacje i sprobuj ponownie.",
    "RECITATION": "Gemini wykryl potencjalna duplikacje tresci. Zmien opis i sprobuj ponownie.",
    "DEADLINE_EXCEEDED": "Przekroczono czas oczekiwania (120s). Sprobuj z mniejsza liczba zdjec.",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
_log_handler = RotatingFileHandler(
    OUTPUT_DIR / "app.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
_log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_log_handler])
logger = logging.getLogger("generator_aukcji")

# ---------------------------------------------------------------------------
# Helpery
# ---------------------------------------------------------------------------


def get_user_error(e):
    """Mapuje wyjatek API na komunikat PL."""
    error_str = str(e)
    for code, msg in ERROR_MESSAGES_PL.items():
        if code in error_str:
            return msg
    return f"Blad API: {error_str[:150]}"


def _validate_image_magic(content: bytes) -> bool:
    """Sprawdza magic bytes pliku. Zwraca True jesli to dozwolony format obrazu."""
    for magic in ALLOWED_IMAGE_MAGIC:
        if content[:len(magic)] == magic:
            return True
    return False


_SAFE_PATH_RE = re.compile(r'^[a-zA-Z0-9_-]+$')


def _validate_path_segment(segment: str, label: str = "parametr") -> None:
    """Waliduje segment sciezki (job_id, key, auction_id). Rzuca 400 przy path traversal."""
    if not segment or not _SAFE_PATH_RE.match(segment):
        raise HTTPException(400, f"Nieprawidlowy {label}")


def _sanitize_feedback(text: str) -> str:
    """Usuwa tagi HTML/JS, prompt injection patterns i ogranicza dlugosc."""
    text = re.sub(r'[<>{}\[\]]', '', text)
    text = re.sub(r'(?i)(ignore|forget|disregard|override)\s+(all|previous|above|instructions)', '', text)
    text = re.sub(r'(?i)(system|assistant|user)\s*:', '', text)
    return text.strip()[:MAX_FEEDBACK_LENGTH]


API_CALL_TIMEOUT_SEC = 120


async def _api_call_with_timeout(coro, timeout: float = API_CALL_TIMEOUT_SEC):
    """Wrapper na asyncio.wait_for z timeout. Rzuca TimeoutError."""
    return await asyncio.wait_for(coro, timeout=timeout)


def _track_cost(session: SessionData, model_name: str, cost: float):
    """Tracking kosztow per model."""
    session.model_costs[model_name] = session.model_costs.get(model_name, 0.0) + cost
    session.total_cost_usd += cost


def sanitize_html(html_text):
    """Usuwa tagi HTML spoza whitelisty, event handlers i atrybuty."""
    html_text = html_lib.unescape(html_text)
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


def _pil_to_png_bytes(pil_img):
    """Konwertuje PIL Image na PNG bytes."""
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()


def generate_image(client, prompt_text, images, task_name):
    """Generuje obraz przez Gemini (domyslnie) lub OpenAI.

    OpenAI wylaczone - problemy z MIME type i wiernością produktu.
    Zwraca PIL Image lub None.
    """
    return _generate_image_gemini(client, prompt_text, images, task_name)


def _generate_image_openai(oai_client, prompt_text, images, task_name):
    """OpenAI GPT Image: images.edit z input_fidelity=high."""
    image_files = [
        (f"image_{i}.png", _pil_to_png_bytes(img), "image/png")
        for i, img in enumerate(images[:5])
    ]

    for attempt in range(1, 4):
        try:
            result = oai_client.images.edit(
                model=OPENAI_IMAGE_MODEL,
                image=image_files if len(image_files) > 1 else image_files[0],
                prompt=prompt_text,
                input_fidelity="high",
                quality="high",
                size="1024x1536",
                n=1,
            )
            if result.data and result.data[0].b64_json:
                img_data = base64.b64decode(result.data[0].b64_json)
                img = PIL.Image.open(io.BytesIO(img_data))
                img.load()
                logger.info(f"Image generated (OpenAI): {task_name}")
                return img
            return None
        except Exception as e:
            error_str = str(e)
            if attempt < 3 and any(code in error_str for code in ["429", "500", "503", "rate_limit"]):
                logger.warning(f"OpenAI retry {attempt}: {task_name} - {error_str[:100]}")
                time.sleep(10 * attempt)
            else:
                raise
    return None


def _generate_image_gemini(client, prompt_text, images, task_name):
    """Gemini fallback: generate_content z IMAGE modality."""
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
                        logger.info(f"Image generated (Gemini): {task_name}")
                        return img
                    except Exception:
                        continue
            return None
        except Exception as e:
            error_str = str(e)
            if attempt < 3 and any(code in error_str for code in ["429", "500", "503", "RESOURCE_EXHAUSTED"]):
                logger.warning(f"Gemini retry {attempt}: {task_name} - {error_str[:100]}")
                time.sleep(10 * attempt)
            else:
                raise
    return None


def remove_background(pil_image):
    """Usuwa tlo ze zdjecia produktu. Zwraca PIL Image RGBA."""
    if not REMBG_AVAILABLE:
        return pil_image.convert("RGBA")
    session = get_rembg_session()
    return rembg_remove(pil_image, session=session)


def create_studio_packshots(transparent_img, original_img=None):
    """Tworzy packshoty: oryginal na czystym bialym tle z miekkim cieniem. Zwraca liste PIL Images."""
    from PIL import ImageFilter

    results = []

    # Packshot 1: oryginalny widok na bialym tle
    canvas = PIL.Image.new("RGBA", (1200, 900), (255, 255, 255, 255))
    # Skaluj produkt zeby zmiescil sie w 80% canvas
    product = transparent_img.copy()
    max_w, max_h = int(1200 * 0.8), int(900 * 0.8)
    ratio = min(max_w / product.width, max_h / product.height)
    if ratio < 1:
        product = product.resize((int(product.width * ratio), int(product.height * ratio)), PIL.Image.LANCZOS)
    # Centruj
    x = (1200 - product.width) // 2
    y = (900 - product.height) // 2
    # Dodaj miekki cien
    shadow = PIL.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow.paste(PIL.Image.new("RGBA", product.size, (0, 0, 0, 40)), (x + 8, y + 8), mask=product.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    canvas = PIL.Image.alpha_composite(canvas, shadow)
    canvas.paste(product, (x, y), mask=product)
    results.append(canvas.convert("RGB"))

    # Packshot 2: jesli mamy oryginal, uzyj go (lepsze swiatlo)
    if original_img:
        canvas2 = PIL.Image.new("RGB", (1200, 900), (255, 255, 255))
        orig = original_img.copy()
        ratio2 = min(max_w / orig.width, max_h / orig.height)
        if ratio2 < 1:
            orig = orig.resize((int(orig.width * ratio2), int(orig.height * ratio2)), PIL.Image.LANCZOS)
        x2 = (1200 - orig.width) // 2
        y2 = (900 - orig.height) // 2
        canvas2.paste(orig, (x2, y2))
        results.append(canvas2)

    return results


async def analyze_product_dna(client, pil_images):
    """Analizuje produkt ze zdjec i zwraca Product DNA jako JSON string."""
    prompt = get_product_dna_prompt()
    response = await _api_call_with_timeout(asyncio.to_thread(
        lambda: client.models.generate_content(
            model=MODEL,
            contents=[prompt] + pil_images[:2],
            config=types.GenerateContentConfig(response_modalities=["TEXT"]),
        )
    ))
    if response.candidates and response.parts:
        for part in response.parts:
            if part.text:
                text = part.text.strip()
                # Wyczysc JSON z ewentualnych blokow ```json
                if text.startswith("```"):
                    lines = text.split("\n")
                    text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
                return text
    return "{}"


async def run_selfcheck(client, original_img, generated_img, product_dna_json):
    """Porownuje wygenerowane zdjecie z oryginalem. Zwraca (score, differences, corrections)."""
    prompt = get_selfcheck_prompt(product_dna_json)
    response = await _api_call_with_timeout(asyncio.to_thread(
        lambda: client.models.generate_content(
            model=MODEL,
            contents=[prompt, original_img, generated_img],
            config=types.GenerateContentConfig(response_modalities=["TEXT"]),
        )
    ))
    if response.candidates and response.parts:
        for part in response.parts:
            if part.text:
                text = part.text.strip()
                if text.startswith("```"):
                    lines = text.split("\n")
                    text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
                try:
                    data = json.loads(text)
                    return (
                        data.get("overall_score", 5),
                        data.get("differences", []),
                        data.get("corrections_needed", ""),
                    )
                except json.JSONDecodeError:
                    pass
    return (5, [], "")


def create_zip(image_paths: dict, description_text: str, output_path: Path):
    """Tworzy ZIP z grafik (plikow z dysku) i opisu produktu.

    image_paths: dict {name: file_path} - sciezki do plikow PNG na dysku.
    """
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, file_path in image_paths.items():
            fp = Path(file_path)
            if not fp.exists():
                continue
            if name.startswith("zdjecie_oryginalne_") or name.startswith("original_"):
                zf.write(fp, f"grafiki/oryginaly/{name}.png")
            else:
                zf.write(fp, f"grafiki/wygenerowane/{name}.png")
        if description_text:
            zf.writestr("opis-produktu.html", description_text)
            zf.writestr("opis-produktu.txt", description_text)


def validate_allegro_title(title):
    """Waliduje tytul Allegro. Zwraca liste {status, text}."""
    checks = []
    length = len(title)
    if 60 <= length <= 75:
        checks.append({"status": "ok", "text": f"{length}/75 zn."})
    elif length < 60:
        checks.append({"status": "warn", "text": f"{length}/75 zn. (za krotki)"})
    else:
        checks.append({"status": "error", "text": f"{length}/75 zn. (za dlugi)"})

    words = title.split()
    caps_words = [w for w in words if len(w) > 3 and w.isupper()]
    if caps_words:
        checks.append({"status": "error", "text": f"CAPS: {', '.join(caps_words)}"})

    banned = ["tanio", "okazja", "nowość", "promocja", "hit"]
    found = [b for b in banned if b.lower() in title.lower()]
    if found:
        checks.append({"status": "error", "text": f"Zakazane: {', '.join(found)}"})
    else:
        checks.append({"status": "ok", "text": "Brak zakazanych"})

    return checks


def _session_cost_pln(session: SessionData) -> float:
    """Oblicza koszt sesji w PLN. Uzywa per-model trackingu jesli dostepny."""
    if session.total_cost_usd > 0:
        return session.total_cost_usd * USD_TO_PLN
    # Fallback na estymacje (stare sesje bez _track_cost)
    image_cost = session.image_gen_count * COST_PER_IMAGE_USD
    text_cost = session.text_gen_count * COST_PER_TEXT_CALL_EST
    return (image_cost + text_cost) * USD_TO_PLN


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def require_auth(request: Request) -> SessionData:
    """Wyciaga token z Bearer header. SSE uzywa jednorazowych ticketow."""
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    if not token:
        raise HTTPException(401, "Brak tokenu autoryzacji")
    session = get_session(token)
    if not session:
        raise HTTPException(401, "Sesja wygasla lub nieprawidlowy token")
    return session


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


async def _cleanup_loop():
    """Periodyczny cleanup sesji i uploads."""
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL)
        cleanup_expired()
        # Cleanup uploads nie powiazanych z aktywna sesja
        if UPLOADS_DIR.exists():
            active_job_ids = {s.job_id for s in sessions.values() if s.job_id}
            for d in UPLOADS_DIR.iterdir():
                if d.is_dir() and d.name not in active_job_ids:
                    try:
                        shutil.rmtree(d)
                    except OSError:
                        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Generator Aukcji API", version="4.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Dodaje naglowki bezpieczenstwa do kazdej odpowiedzi."""

    async def dispatch(self, request: Request, call_next):
        response: StarletteResponse = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


app.add_middleware(SecurityHeadersMiddleware)


# ---------------------------------------------------------------------------
# Endpointy
# ---------------------------------------------------------------------------


def _verify_password(plain: str, stored: str) -> bool:
    """Weryfikuje haslo. Obsluguje bcrypt hash ($2b$) i plain text (legacy)."""
    if stored.startswith("$2b$") or stored.startswith("$2a$"):
        return bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
    return hmac.compare_digest(plain, stored)


@app.post("/api/auth")
async def auth(request: Request):
    """Logowanie: sprawdza haslo, tworzy sesje, zwraca token."""
    body = await request.json()
    password = body.get("password", "")
    app_password = get_secret("APP_PASSWORD", "")
    ip = get_client_ip(request)

    # Lockout check
    remaining = check_lockout(ip)
    if remaining > 0:
        raise HTTPException(429, f"Za duzo prob. Odczekaj {remaining} sekund.")

    if not app_password:
        raise HTTPException(503, "Serwer nie skonfigurowany. Ustaw APP_PASSWORD.")

    if not _verify_password(password, app_password):
        record_failed_login(ip)
        raise HTTPException(401, "Nieprawidlowe haslo")

    reset_lockout(ip)
    try:
        session = create_session(max_sessions=MAX_CONCURRENT_SESSIONS)
    except TooManySessions:
        raise HTTPException(429, "Za duzo aktywnych sesji. Sprobuj pozniej.")
    return {"token": session.token}


@app.get("/api/session/stats")
async def session_stats(session: SessionData = Depends(require_auth)):
    """Statystyki sesji: liczniki API, koszt."""
    return {
        "api_calls_count": session.api_calls_count,
        "image_gen_count": session.image_gen_count,
        "text_gen_count": session.text_gen_count,
        "cost_pln": round(_session_cost_pln(session), 2),
        "max_api_calls": MAX_API_CALLS_PER_SESSION,
        "max_regen": MAX_REGEN_PER_SESSION,
    }


@app.get("/api/catalogs")
async def catalogs_list():
    """Lista katalogow produktowych."""
    names = get_catalog_display_names()
    return [{"key": k, "name": v} for k, v in names.items()]


@app.get("/api/catalogs/{key}/categories")
async def catalog_categories(key: str):
    """Kategorie dla katalogu."""
    cats = get_categories(key)
    if not cats:
        raise HTTPException(404, f"Katalog '{key}' nie istnieje")
    return cats


@app.get("/api/catalogs/{key}/colors")
async def catalog_colors(key: str):
    """Kolory dla katalogu."""
    kolor_map = get_kolor_map(key)
    kolory_pe = get_kolory_per_element(key)
    return {"kolor_map": kolor_map, "kolory_per_element": kolory_pe}


@app.post("/api/analyze")
async def analyze_product(request: Request, session: SessionData = Depends(require_auth)):
    """Krok 1 nowego flow: AI analizuje zdjecia + specyfikacje i zwraca sugestie.

    Marcin potwierdza/modyfikuje sugestie, potem generuje.
    Input: multipart/form-data (catalog_key, specyfikacja, files).
    Output: JSON z sugestiami kategorii, kolorow, features.
    """
    form = await request.form()

    catalog_key = form.get("catalog_key", "")
    specyfikacja = form.get("specyfikacja", "")

    if not catalog_key:
        raise HTTPException(400, "Brak catalog_key.")

    categories = get_categories(catalog_key)
    if not categories:
        raise HTTPException(404, f"Katalog '{catalog_key}' nie istnieje.")

    spec_stripped = specyfikacja.strip() if isinstance(specyfikacja, str) else ""
    if not spec_stripped:
        raise HTTPException(400, "Wklej specyfikacje produktu.")
    if len(spec_stripped) > 5000:
        raise HTTPException(400, f"Specyfikacja za dluga ({len(spec_stripped)} zn.). Maksimum: 5000.")

    # Walidacja plikow
    files = form.getlist("files")
    if not files:
        raise HTTPException(400, "Wgraj co najmniej 1 zdjecie produktu.")
    if len(files) > MAX_FILES:
        raise HTTPException(400, f"Za duzo plikow ({len(files)}). Maksimum: {MAX_FILES}.")

    # Limit API
    if session.api_calls_count >= MAX_API_CALLS_PER_SESSION:
        raise HTTPException(429, f"Osiagnieto limit {MAX_API_CALLS_PER_SESSION} zapytan w tej sesji.")

    # Zapisz pliki na dysk
    analysis_id = uuid.uuid4().hex[:12]
    job_dir = UPLOADS_DIR / analysis_id
    job_dir.mkdir(parents=True, exist_ok=True)
    source_paths = []

    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    for i, file_field in enumerate(files):
        if hasattr(file_field, 'read'):
            content = await file_field.read()
        else:
            content = file_field if isinstance(file_field, bytes) else str(file_field).encode()
        if len(content) > max_bytes:
            raise HTTPException(400, f"Plik {i+1} jest za duzy. Maksymalny rozmiar: {MAX_UPLOAD_SIZE_MB} MB.")
        if not _validate_image_magic(content):
            raise HTTPException(400, f"Plik {i+1}: niedozwolony format. Dozwolone: JPEG, PNG, WebP.")
        path = job_dir / f"source_{i}.png"
        path.write_bytes(content)
        source_paths.append(str(path))

    # Zaladuj PIL images
    api_key = get_secret("GEMINI_API_KEY")
    if not api_key or not GENAI_AVAILABLE:
        raise HTTPException(500, "Brak konfiguracji Gemini API.")

    pil_images = []
    for sp in source_paths:
        try:
            img = PIL.Image.open(sp)
            img.load()
            pil_images.append(img)
        except Exception:
            pass

    if not pil_images:
        raise HTTPException(400, "Zadne zdjecie nie zostalo wczytane.")

    # Przygotuj dane do promptu
    kolory_pe = get_kolory_per_element(catalog_key)
    features_info = get_features_for_type(categories[0] if categories else "")

    # Buduj prompt analizy
    prompt = get_analysis_prompt(
        spec_text=spec_stripped,
        catalog_name=catalog_key,
        available_categories=categories,
        available_colors=kolory_pe,
        required_features=features_info["required"],
    )

    # Wywolaj Gemini
    client = genai.Client(api_key=api_key)
    contents = [prompt] + pil_images[:4]

    try:
        response = await _api_call_with_timeout(asyncio.to_thread(
            lambda: client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(response_modalities=["TEXT"]),
            )
        ))
    except asyncio.TimeoutError:
        raise HTTPException(504, "Przekroczono czas oczekiwania na Gemini (120s)")
    except Exception as e:
        raise HTTPException(500, get_user_error(e))

    session.api_calls_count += 1
    session.text_gen_count += 1

    if not response.parts:
        raise HTTPException(500, "Gemini nie zwrocil odpowiedzi.")

    raw_text = ""
    for part in response.parts:
        if part.text:
            raw_text += part.text

    # Parsuj JSON z odpowiedzi
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

    try:
        suggestions = json.loads(raw_text)
    except json.JSONDecodeError:
        raise HTTPException(500, "Gemini nie zwrocil prawidlowego JSON. Sprobuj ponownie.")

    # Zapisz w sesji
    analysis_data = {
        "analysis_id": analysis_id,
        "suggestions": suggestions,
        "catalog_key": catalog_key,
        "specyfikacja": spec_stripped,
        "source_paths": source_paths,
    }
    session.last_analysis = analysis_data

    # Buduj response
    return {
        "analysis_id": analysis_id,
        "suggestions": suggestions,
        "available_categories": categories,
        "available_colors": kolory_pe,
    }


@app.post("/api/generate")
async def generate(request: Request, session: SessionData = Depends(require_auth)):
    """Uruchamia generowanie aukcji. Zwraca job_id do sledzenia przez SSE."""
    form = await request.form()

    # Parsuj pola formularza
    catalog_key = form.get("catalog_key", "")
    kategoria = form.get("kategoria", "")
    specyfikacja = form.get("specyfikacja", "")
    kolor_zlew = form.get("kolor_zlew", "Czarny nakrapiany")
    kolor_bateria = form.get("kolor_bateria", "Czarno-zlota")
    kolor_syfon = form.get("kolor_syfon", "Zloty")
    kolor_dozownik = form.get("kolor_dozownik", "Zloty")
    ean_code = form.get("ean_code", "")
    # Nowy flow: opcjonalne pola z analizy
    analysis_id = form.get("analysis_id", "")
    confirmed_kategoria = form.get("confirmed_kategoria", "")
    confirmed_kolory_raw = form.get("confirmed_kolory", "")
    confirmed_features_raw = form.get("confirmed_features", "")
    try:
        cena_brutto = float(form.get("cena_brutto", 0))
    except (ValueError, TypeError):
        cena_brutto = 0.0
    try:
        stan_magazyn = int(form.get("stan_magazyn", 1))
    except (ValueError, TypeError):
        stan_magazyn = 1

    # Jesli podano analysis_id, pobierz sugestie z sesji
    if analysis_id and session.last_analysis and session.last_analysis.get("analysis_id") == analysis_id:
        analysis = session.last_analysis
        suggestions = analysis.get("suggestions", {})

        # Uzyj confirmed_* lub fallback na sugestie AI
        if confirmed_kategoria:
            kategoria = confirmed_kategoria
        elif not kategoria and suggestions.get("kategoria"):
            kategoria = suggestions["kategoria"]

        if not catalog_key and analysis.get("catalog_key"):
            catalog_key = analysis["catalog_key"]

        if not specyfikacja and analysis.get("specyfikacja"):
            specyfikacja = analysis["specyfikacja"]

        # Kolory: confirmed > form > sugestie AI
        if confirmed_kolory_raw:
            try:
                confirmed_kolory = json.loads(confirmed_kolory_raw)
                kolor_zlew = confirmed_kolory.get("zlew", kolor_zlew)
                kolor_bateria = confirmed_kolory.get("bateria", kolor_bateria)
                kolor_syfon = confirmed_kolory.get("syfon", kolor_syfon)
                kolor_dozownik = confirmed_kolory.get("dozownik", kolor_dozownik)
            except json.JSONDecodeError:
                pass
        elif suggestions.get("kolory"):
            s_kolory = suggestions["kolory"]
            if s_kolory.get("zlew") and kolor_zlew == "Czarny nakrapiany":
                kolor_zlew = s_kolory["zlew"]
            if s_kolory.get("bateria") and kolor_bateria == "Czarno-zlota":
                kolor_bateria = s_kolory["bateria"]
            if s_kolory.get("syfon") and kolor_syfon == "Zloty":
                kolor_syfon = s_kolory["syfon"]
            if s_kolory.get("dozownik") and kolor_dozownik == "Zloty":
                kolor_dozownik = s_kolory["dozownik"]

        # Features: zapisz w sesji do uzycia przy push
        if confirmed_features_raw:
            try:
                session.last_analysis["confirmed_features"] = json.loads(confirmed_features_raw)
            except json.JSONDecodeError:
                pass
        elif suggestions.get("features"):
            session.last_analysis["confirmed_features"] = suggestions["features"]

    if not catalog_key:
        raise HTTPException(400, "Brak catalog_key.")
    if not kategoria:
        raise HTTPException(400, "Brak kategorii.")

    # Walidacja plikow - jesli analysis_id, zdjecia juz sa na dysku
    files = form.getlist("files")
    source_paths = []
    job_id = uuid.uuid4().hex[:12]
    job_dir = UPLOADS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    if not files and analysis_id and session.last_analysis:
        # Uzyj zdjec z analizy
        analysis_source = session.last_analysis.get("source_paths", [])
        if not analysis_source:
            raise HTTPException(400, "Wgraj co najmniej 1 zdjecie produktu.")
        for i, sp in enumerate(analysis_source):
            if Path(sp).exists():
                dest = job_dir / f"source_{i}.png"
                shutil.copy2(sp, dest)
                source_paths.append(str(dest))
        if not source_paths:
            raise HTTPException(400, "Zdjecia z analizy nie sa juz dostepne. Wgraj ponownie.")
    elif files:
        if len(files) > MAX_FILES:
            raise HTTPException(400, f"Za duzo plikow ({len(files)}). Maksimum: {MAX_FILES}.")
        gen_max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
        for i, file_field in enumerate(files):
            if hasattr(file_field, 'read'):
                content = await file_field.read()
            else:
                content = file_field if isinstance(file_field, bytes) else str(file_field).encode()
            if len(content) > gen_max_bytes:
                raise HTTPException(400, f"Plik {i+1} jest za duzy. Maksymalny rozmiar: {MAX_UPLOAD_SIZE_MB} MB.")
            if not _validate_image_magic(content):
                raise HTTPException(400, f"Plik {i+1}: niedozwolony format. Dozwolone: JPEG, PNG, WebP.")
            path = job_dir / f"source_{i}.png"
            path.write_bytes(content)
            source_paths.append(str(path))
    else:
        raise HTTPException(400, "Wgraj co najmniej 1 zdjecie produktu.")

    # Walidacja specyfikacji
    spec_stripped = specyfikacja.strip() if isinstance(specyfikacja, str) else ""
    if not spec_stripped:
        raise HTTPException(400, "Wklej specyfikacje produktu.")
    if len(spec_stripped) > 5000:
        raise HTTPException(400, f"Specyfikacja za dluga ({len(spec_stripped)} zn.). Maksimum: 5000.")

    # Limit API
    if session.api_calls_count >= MAX_API_CALLS_PER_SESSION:
        raise HTTPException(429, f"Osiagnieto limit {MAX_API_CALLS_PER_SESSION} generowan w tej sesji.")

    # Ustawienia sesji
    session.job_id = job_id
    session.job_status = "running"
    session.job_progress = 0.0
    session.job_message = ""
    session.job_error = ""
    session.results_dir = str(job_dir)
    session.results_images = {}
    session.results_sections = {}
    session.results_desc_raw = ""
    session.results_timestamp = ""
    session.source_image_paths = source_paths
    session.last_catalog = catalog_key
    session.last_kategoria = kategoria
    session.last_kolory = {
        "kolor_zlew": kolor_zlew,
        "kolor_bateria": kolor_bateria,
        "kolor_syfon": kolor_syfon,
        "kolor_dozownik": kolor_dozownik,
    }
    session.image_chat_history = {}
    session.description_revisions = []
    session.desc_chat_history = []
    session.sse_queue = asyncio.Queue()

    # Background task
    asyncio.create_task(_run_generation(
        session, job_id, job_dir, source_paths,
        catalog_key, kategoria, spec_stripped,
        kolor_zlew, kolor_bateria, kolor_syfon, kolor_dozownik,
        ean_code, cena_brutto, stan_magazyn,
    ))

    return {"job_id": job_id}


@app.post("/api/generate/stream-ticket")
async def generate_stream_ticket(session: SessionData = Depends(require_auth)):
    """Tworzy jednorazowy ticket SSE (30s TTL). Token sesji NIE trafia do URL."""
    ticket = create_sse_ticket(session.token)
    return {"ticket": ticket}


@app.get("/api/generate/stream/{job_id}")
async def generate_stream(job_id: str, request: Request, ticket: str = Query("")):
    """SSE stream dla postepow generowania."""
    # Auth: jednorazowy ticket (token sesji NIE w URL)
    if not ticket:
        raise HTTPException(401, "Brak ticketu SSE. Uzyj POST /api/generate/stream-ticket")
    session = validate_sse_ticket(ticket)
    if not session:
        raise HTTPException(401, "Ticket wygasl lub juz uzyty")
    if session.job_id != job_id:
        raise HTTPException(404, "Nieznany job_id")

    async def event_generator():
        # Jesli job juz zakonczony
        if session.job_status in ("done", "error"):
            if session.job_status == "error":
                yield f"event: error\ndata: {json.dumps({'message': session.job_error})}\n\n"
            else:
                yield f"event: complete\ndata: {json.dumps({'message': 'Zakonczono'})}\n\n"
            return

        queue = session.sse_queue
        if queue is None:
            yield f"event: error\ndata: {json.dumps({'message': 'Brak kolejki SSE'})}\n\n"
            return

        while True:
            if await request.is_disconnected():
                break

            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
            except asyncio.TimeoutError:
                if await request.is_disconnected():
                    break
                # Keep-alive ping
                yield ": ping\n\n"
                continue

            if event is None:
                break

            event_type = event.get("type", "progress")
            data = event.get("data", {})
            yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

            if event_type in ("complete", "error"):
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/images/{job_id}/{key}")
async def get_image(job_id: str, key: str, session: SessionData = Depends(require_auth)):
    """Serwuje wygenerowany obraz."""
    _validate_path_segment(job_id, "job_id")
    _validate_path_segment(key, "key")

    # Szukaj w results_images
    file_path = session.results_images.get(key)
    if file_path and Path(file_path).exists():
        resolved = Path(file_path).resolve()
        if not str(resolved).startswith(str(BASE_DIR.resolve())):
            raise HTTPException(403, "Niedozwolona sciezka")
        return FileResponse(resolved, media_type="image/png")

    # Fallback: uploads/{job_id}/{key}.png
    fallback = (UPLOADS_DIR / job_id / f"{key}.png").resolve()
    if not str(fallback).startswith(str(UPLOADS_DIR.resolve())):
        raise HTTPException(403, "Niedozwolona sciezka")
    if fallback.exists():
        return FileResponse(fallback, media_type="image/png")

    raise HTTPException(404, "Obraz nie znaleziony")


@app.get("/api/results/{job_id}")
async def get_results(job_id: str, session: SessionData = Depends(require_auth)):
    """Zwraca wyniki generowania."""
    _validate_path_segment(job_id, "job_id")
    if session.job_id != job_id:
        raise HTTPException(404, "Nieznany job_id")

    images_urls = {}
    for key in session.results_images:
        images_urls[key] = f"/api/images/{job_id}/{key}"

    return {
        "status": session.job_status,
        "sections": session.results_sections,
        "desc_raw": session.results_desc_raw,
        "images": images_urls,
        "timestamp": session.results_timestamp,
        "cost_pln": round(_session_cost_pln(session), 2),
    }


@app.get("/api/results/{job_id}/zip")
async def get_results_zip(job_id: str, session: SessionData = Depends(require_auth)):
    """Pobiera ZIP z grafikami i opisem."""
    _validate_path_segment(job_id, "job_id")
    if session.job_id != job_id:
        raise HTTPException(404, "Nieznany job_id")
    if not session.results_images:
        raise HTTPException(404, "Brak wynikow do pobrania")

    timestamp = session.results_timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = OUTPUT_DIR / f"aukcja_{timestamp}.zip"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    desc_text = session.results_sections.get("opis", "") or session.results_desc_raw
    create_zip(session.results_images, desc_text, zip_path)
    cleanup_old_outputs(OUTPUT_DIR, max_files=50)

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"aukcja_{timestamp}.zip",
    )


@app.post("/api/chat/image")
async def chat_image(request: Request, session: SessionData = Depends(require_auth)):
    """Edycja grafiki przez czat (regeneracja Gemini)."""
    body = await request.json()
    image_key = body.get("image_key", "")
    instruction = _sanitize_feedback(body.get("instruction", ""))

    if not image_key:
        raise HTTPException(400, "Brak image_key")
    if not instruction:
        raise HTTPException(400, "Brak instrukcji")
    if session.regen_count >= MAX_REGEN_PER_SESSION:
        raise HTTPException(429, f"Limit regeneracji ({MAX_REGEN_PER_SESSION}) osiagniety.")

    # Laduj obraz z dysku
    file_path = session.results_images.get(image_key)
    if not file_path or not Path(file_path).exists():
        raise HTTPException(404, f"Obraz '{image_key}' nie znaleziony")

    api_key = get_secret("GEMINI_API_KEY")
    if not api_key or not GENAI_AVAILABLE:
        raise HTTPException(500, "Brak konfiguracji Gemini API")

    client = genai.Client(api_key=api_key)

    # Laduj aktualny obraz
    current_img = PIL.Image.open(file_path)
    current_img.load()

    # Source images
    source_imgs = []
    for sp in session.source_image_paths[:2]:
        if Path(sp).exists():
            img = PIL.Image.open(sp)
            img.load()
            source_imgs.append(img)

    if REGEN_AVAILABLE:
        full_prompt = get_regen_prompt("edit", instruction)
    else:
        full_prompt = (
            f"Modify this product image: {instruction}. "
            f"Professional product photography quality. High resolution. "
            f"Do NOT add text, labels, watermarks."
        )

    regen_images = [current_img] + source_imgs

    try:
        new_img = await asyncio.to_thread(generate_image, client, full_prompt, regen_images, f"Chat edit: {image_key}")
    except Exception as e:
        return {"success": False, "message": get_user_error(e)}
    finally:
        current_img.close()
        for _si in source_imgs:
            _si.close()

    if not new_img:
        return {"success": False, "message": "Gemini nie zwrocil obrazu. Sprobuj ponownie."}

    # Zapisz nowy obraz
    job_dir = Path(session.results_dir) if session.results_dir else UPLOADS_DIR / (session.job_id or "unknown")
    job_dir.mkdir(parents=True, exist_ok=True)
    new_path = job_dir / f"{image_key}.png"
    new_img.save(str(new_path))
    new_img.close()
    session.results_images[image_key] = str(new_path)

    session.regen_count += 1
    session.api_calls_count += 1
    session.image_gen_count += 1

    # Chat history
    if image_key not in session.image_chat_history:
        session.image_chat_history[image_key] = []
    session.image_chat_history[image_key].append({
        "instruction": instruction,
        "timestamp": datetime.now().isoformat(),
    })

    return {
        "success": True,
        "url": f"/api/images/{session.job_id}/{image_key}",
        "message": "Grafika zaktualizowana.",
    }


@app.post("/api/chat/description")
async def chat_description(request: Request, session: SessionData = Depends(require_auth)):
    """Poprawka opisu aukcji przez czat lub reczna edycja HTML."""
    body = await request.json()
    instruction = _sanitize_feedback(body.get("instruction", ""))
    manual_html = body.get("manual_html", "").strip()

    current_desc = session.results_sections.get("opis", "") or session.results_desc_raw

    # Manual HTML edit
    if manual_html:
        safe_html = sanitize_html(manual_html)
        session.description_revisions.append(current_desc)
        session.results_sections["opis"] = safe_html
        session.results_desc_raw = safe_html
        return {"success": True, "html": safe_html, "message": "Opis zaktualizowany recznie."}

    if not instruction:
        raise HTTPException(400, "Brak instrukcji lub manual_html")

    # Limit rewizji
    if len(session.description_revisions) >= 5:
        raise HTTPException(429, "Limit rewizji opisu (5) osiagniety.")

    api_key = get_secret("GEMINI_API_KEY")
    if not api_key or not GENAI_AVAILABLE:
        raise HTTPException(500, "Brak konfiguracji Gemini API")

    client = genai.Client(api_key=api_key)
    prompt = get_description_revision_prompt(current_desc, instruction)

    try:
        response = await _api_call_with_timeout(asyncio.to_thread(
            lambda: client.models.generate_content(
                model=MODEL,
                contents=[prompt],
                config=types.GenerateContentConfig(response_modalities=["TEXT"]),
            )
        ))
    except asyncio.TimeoutError:
        return {"success": False, "message": "Przekroczono czas oczekiwania (120s)"}
    except Exception as e:
        return {"success": False, "message": get_user_error(e)}

    if not response.parts:
        return {"success": False, "message": "Gemini nie zwrocil odpowiedzi."}

    new_html = ""
    for part in response.parts:
        if part.text:
            new_html += part.text

    new_html = new_html.strip()
    # Usun markdown code block
    if new_html.startswith("```"):
        lines = new_html.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        new_html = "\n".join(lines)

    safe_html = sanitize_html(new_html)
    banned = check_ban_list(safe_html)

    # Zapisz rewizje
    session.description_revisions.append(current_desc)
    session.results_sections["opis"] = safe_html
    session.results_desc_raw = safe_html
    session.api_calls_count += 1
    session.text_gen_count += 1

    session.desc_chat_history.append({
        "instruction": instruction,
        "timestamp": datetime.now().isoformat(),
    })

    return {
        "success": True,
        "html": safe_html,
        "message": "Opis zaktualizowany.",
        "banned": banned,
    }


@app.post("/api/chat/description/undo")
async def chat_description_undo(session: SessionData = Depends(require_auth)):
    """Cofa ostatnia rewizje opisu."""
    if not session.description_revisions:
        raise HTTPException(400, "Brak rewizji do cofniecia.")

    previous = session.description_revisions.pop()
    session.results_sections["opis"] = previous
    session.results_desc_raw = previous

    return {"success": True, "html": previous, "message": "Cofnieto ostatnia zmiane."}


@app.post("/api/baselinker/test")
async def baselinker_test(request: Request, session: SessionData = Depends(require_auth)):
    """Test polaczenia z BaseLinker."""
    body = await request.json()
    inventory_id = body.get("inventory_id", 0)
    bl_token = get_secret("BASELINKER_TOKEN")
    if not bl_token:
        return {"success": False, "message": "Brak BASELINKER_TOKEN w konfiguracji."}

    try:
        result = await asyncio.to_thread(
            bl_request, "getInventoryProductsList", {"inventory_id": inventory_id}, bl_token
        )
        return {"success": True, "message": "Polaczenie OK. Znaleziono produkty w katalogu."}
    except Exception as e:
        return {"success": False, "message": str(e)[:200]}


@app.post("/api/baselinker/push")
async def baselinker_push(request: Request, session: SessionData = Depends(require_auth)):
    """Wysyla produkt do BaseLinker."""
    body = await request.json()
    name = body.get("name", "")
    description = body.get("description", "")
    sku = body.get("sku", "")
    cena_brutto = body.get("cena_brutto", 0)
    stan_magazyn = body.get("stan_magazyn", 1)
    ean_code = body.get("ean_code", "")
    waga_kg = body.get("waga_kg", 0)
    wysokosc_cm = body.get("wysokosc_cm", 0)
    szerokosc_cm = body.get("szerokosc_cm", 0)
    dlugosc_cm = body.get("dlugosc_cm", 0)
    features = body.get("features", {})
    inventory_id = body.get("inventory_id", int(get_secret("BASELINKER_INVENTORY_ID", "8075")))
    price_group_id = body.get("price_group_id", int(get_secret("BASELINKER_PRICE_GROUP_ID", "3778")))
    warehouse_id = body.get("warehouse_id", get_secret("BASELINKER_WAREHOUSE_ID", "bl_5255"))
    force_overwrite = body.get("force_overwrite", False)

    # Fallback: features z analizy (jesli nie podano w body)
    if not features and session.last_analysis:
        features = session.last_analysis.get("confirmed_features", {})

    bl_token = get_secret("BASELINKER_TOKEN")
    if not bl_token:
        return {"success": False, "message": "Brak BASELINKER_TOKEN w konfiguracji."}

    # Blokada cena = 0
    if cena_brutto == 0:
        return {"success": False, "message": "Cena = 0.00 zl. Ustaw cene > 0 przed wysylka."}

    # Deduplikacja SKU
    try:
        existing_id = await asyncio.to_thread(check_sku_exists, bl_token, inventory_id, sku)
    except Exception as e:
        logger.warning(f"check_sku_exists failed for {sku}: {e!s:.200}")
        existing_id = None

    if existing_id and not force_overwrite:
        return {
            "success": False,
            "duplicate": True,
            "existing_id": existing_id,
            "message": f"Produkt z SKU '{sku}' juz istnieje (ID: {existing_id}). Uzyj force_overwrite=true.",
        }

    # Laduj obrazy PIL z dysku (bez oryginalow)
    images_dict = {}
    for key, file_path in session.results_images.items():
        if key.startswith("zdjecie_oryginalne_") or key.startswith("original_"):
            continue
        fp = Path(file_path)
        if fp.exists() and PIL_AVAILABLE:
            try:
                img = PIL.Image.open(fp)
                img.load()
                images_dict[key] = img
            except Exception:
                continue

    catalog_name = session.last_catalog or None
    kategoria = session.last_kategoria or None

    try:
        result = await asyncio.to_thread(
            send_to_baselinker,
            token=bl_token,
            inventory_id=inventory_id,
            price_group_id=price_group_id,
            warehouse_id=warehouse_id,
            name=name,
            description_html=description,
            images_dict=images_dict,
            price=cena_brutto,
            sku=sku,
            stock=stan_magazyn,
            ean=ean_code,
            weight=waga_kg,
            height=wysokosc_cm,
            width=szerokosc_cm,
            length=dlugosc_cm,
            catalog_name=catalog_name,
            kategoria=kategoria,
            features=features,
        )
        product_id = result.get("product_id", "?")
        return {"success": True, "product_id": product_id, "message": f"Wyslano do BaseLinker (ID: {product_id})"}
    except Exception as e:
        return {"success": False, "message": str(e)[:200]}
    finally:
        for _img in images_dict.values():
            _img.close()


@app.get("/api/history")
async def history_list(session: SessionData = Depends(require_auth)):
    """Lista ostatnich aukcji (max 20)."""
    auctions = list_auctions()
    return auctions[:20]


@app.post("/api/draft/save")
async def draft_save(request: Request, session: SessionData = Depends(require_auth)):
    """Zapisuje aktualny stan jako szkic."""
    # Buduj grafiki_b64 z plikow na dysku
    grafiki_b64 = {}
    for key, file_path in session.results_images.items():
        if key.startswith("zdjecie_oryginalne_") or key.startswith("original_"):
            continue
        fp = Path(file_path)
        if fp.exists():
            try:
                grafiki_b64[key] = base64.b64encode(fp.read_bytes()).decode()
            except Exception:
                pass

    sections = session.results_sections
    catalog_key = session.last_catalog or ""
    kategoria = session.last_kategoria or ""

    auction_data = {
        "kategoria": f"{catalog_key} / {kategoria}" if catalog_key else kategoria,
        "kolory": session.last_kolory,
        "grafiki": grafiki_b64,
        "opis": sections.get("opis", "") or session.results_desc_raw,
        "specyfikacja": session.results_desc_raw,
        "tytul": sections.get("tytul", ""),
        "sku": sections.get("sku", ""),
        "bullets": sections.get("bullets", ""),
        "description_revisions": session.description_revisions,
    }

    aid = save_auction(auction_data, "szkic", session.last_auto_draft_id)
    session.last_auto_draft_id = aid

    return {"success": True, "auction_id": aid}


@app.get("/api/draft/{auction_id}")
async def draft_load(auction_id: str, session: SessionData = Depends(require_auth)):
    """Laduje szkic aukcji."""
    _validate_path_segment(auction_id, "auction_id")
    data = load_auction(auction_id)
    if not data:
        raise HTTPException(404, "Szkic nie znaleziony")
    return data


@app.get("/api/history/export")
async def history_export(session: SessionData = Depends(require_auth)):
    """Eksportuje wszystkie aukcje jako ZIP."""
    data = export_all_auctions()
    if not data:
        raise HTTPException(404, "Brak aukcji do eksportu")

    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=aukcje_backup_{datetime.now().strftime('%Y%m%d')}.zip"
        },
    )


# ---------------------------------------------------------------------------
# Pipeline v3.0: Bramki fazowe (approve/feedback/status)
# ---------------------------------------------------------------------------


@app.post("/api/generate/approve")
async def approve_phase(request: Request, session: SessionData = Depends(require_auth)):
    """Akceptacja biezacej fazy (phase1_approval lub phase2_approval)."""
    if not session.job_id:
        return JSONResponse({"error": "Brak aktywnego generowania"}, status_code=400)
    if session.current_phase not in ("phase1_approval", "phase2_approval"):
        return JSONResponse(
            {"error": f"Nie jestes w fazie akceptacji, biezaca: {session.current_phase}"},
            status_code=400,
        )
    session.phase_approved = True
    session.phase_feedback = ""
    if session.phase_event:
        session.phase_event.set()
    return {"status": "approved", "phase": session.current_phase}


@app.post("/api/generate/feedback")
async def phase_feedback(request: Request, session: SessionData = Depends(require_auth)):
    """Feedback do biezacej fazy (popraw i regeneruj)."""
    if not session.job_id:
        return JSONResponse({"error": "Brak aktywnego generowania"}, status_code=400)
    if session.current_phase not in ("phase1_approval", "phase2_approval"):
        return JSONResponse(
            {"error": "Nie jestes w fazie akceptacji"},
            status_code=400,
        )
    body = await request.json()
    feedback = _sanitize_feedback(body.get("feedback", ""))
    session.phase_approved = False
    session.phase_feedback = feedback
    session.phase_round += 1
    if session.phase_event:
        session.phase_event.set()
    return {"status": "feedback_received", "round": session.phase_round}


@app.get("/api/generate/status")
async def generation_status(session: SessionData = Depends(require_auth)):
    """Status generowania (SSE reconnect)."""
    return {
        "phase": session.current_phase,
        "progress": session.job_progress,
        "message": session.job_message,
        "round": session.phase_round,
        "mode": session.generation_mode,
        "cost_usd": session.total_cost_usd,
        "model_costs": session.model_costs,
    }


@app.post("/api/generate/cancel")
async def cancel_generation(request: Request, session: SessionData = Depends(require_auth)):
    """Anuluj trwajace generowanie."""
    if not session.job_id:
        return JSONResponse({"error": "Brak aktywnego generowania"}, status_code=400)
    session.cancel_requested = True
    session.job_status = "idle"
    session.current_phase = "idle"
    if session.sse_queue:
        await session.sse_queue.put({"event": "cancelled", "data": {"message": "Anulowano"}})
    return {"status": "cancelled"}


@app.get("/api/providers/status")
async def providers_status(session: SessionData = Depends(require_auth)):
    """Health check providerow obrazow."""
    return await get_provider_status()


# ---------------------------------------------------------------------------
# LoRA Training Endpoints
# ---------------------------------------------------------------------------

_lora_trainer = LoRATrainer()
_lora_training_task: asyncio.Task | None = None
_lora_training_status: dict = {"status": "idle"}


@app.post("/api/lora/train")
async def lora_train(request: Request, session: SessionData = Depends(require_auth)):
    """Uruchom trening LoRA na zdjeciach z folderu training/."""
    global _lora_training_task, _lora_training_status

    if _lora_training_task and not _lora_training_task.done():
        raise HTTPException(409, "Trening juz w toku")

    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    steps = body.get("steps", 1000)
    image_dir = body.get("image_dir", "training")

    _lora_training_status = {
        "status": "preparing",
        "steps": steps,
        "started_at": datetime.now().isoformat(),
    }

    async def _run_training():
        global _lora_training_status
        try:
            _lora_training_status["status"] = "training"
            result = await quick_train(image_dir=image_dir, steps=steps)
            import config
            config.LORA_MODEL_PATH = result["lora_url"]
            _lora_training_status = {
                "status": "completed",
                "version": result["version"],
                "lora_url": result["lora_url"],
                "cost_usd": result["cost_usd"],
                "validation": result["validation"],
                "completed_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"LoRA training failed: {e}")
            _lora_training_status = {
                "status": "error",
                "error": str(e)[:500],
                "failed_at": datetime.now().isoformat(),
            }

    _lora_training_task = asyncio.create_task(_run_training())

    return {
        "message": "Trening LoRA uruchomiony",
        "steps": steps,
        "estimated_cost_usd": round(steps * 0.008, 2),
    }


@app.get("/api/lora/status")
async def lora_status(session: SessionData = Depends(require_auth)):
    """Status aktualnego treningu LoRA."""
    return _lora_training_status


@app.get("/api/lora/versions")
async def lora_versions(session: SessionData = Depends(require_auth)):
    """Lista wszystkich wersji LoRA."""
    return _lora_trainer.get_registry()


@app.post("/api/lora/test")
async def lora_test(request: Request, session: SessionData = Depends(require_auth)):
    """Uruchom quality gate na aktywnej wersji LoRA."""
    lora_url = _lora_trainer.get_active_lora_url()
    if not lora_url:
        raise HTTPException(404, "Brak aktywnej wersji LoRA")

    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    prompts = body.get("prompts", None)

    result = await _lora_trainer.validate(lora_url, prompts)
    return result


@app.post("/api/lora/rollback/{version}")
async def lora_rollback(version: str, session: SessionData = Depends(require_auth)):
    """Przywroc wczesniejsza wersje LoRA."""
    success = await _lora_trainer.rollback(version)
    if not success:
        raise HTTPException(404, f"Wersja {version} nie istnieje")

    return {"message": f"Rollback do {version}", "active": version}


# ---------------------------------------------------------------------------
# Background generation task
# ---------------------------------------------------------------------------


async def _send_event(queue: asyncio.Queue | None, event_type: str, data: dict):
    """Wysyla event SSE do kolejki sesji."""
    if queue is not None:
        await queue.put({"type": event_type, "data": data})


async def _run_generation(
    session: SessionData,
    job_id: str,
    job_dir: Path,
    source_paths: list[str],
    catalog_key: str,
    kategoria: str,
    specyfikacja: str,
    kolor_zlew: str,
    kolor_bateria: str,
    kolor_syfon: str,
    kolor_dozownik: str,
    ean_code: str,
    cena_brutto: float,
    stan_magazyn: int,
):
    """Pipeline v3.0: 2-fazowy flow z bramkami approve/feedback.

    [0] rembg -> transparent PNG
    [1] Gemini TEXT -> Product DNA
    FAZA 1: Packshoty (Pillow + Gemini composite) -> BRAMKA
    FAZA 2: Lifestyle (6 scen + selfcheck) -> BRAMKA
    FINALIZACJA: Opis B2C
    """
    queue = session.sse_queue
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session.results_timestamp = timestamp
    pil_images: list = []
    transparent_images: list = []

    def _check_cancel() -> bool:
        """Sprawdza czy uzytkownik anulował generowanie."""
        if session.cancel_requested:
            session.job_status = "idle"
            session.current_phase = "idle"
            return True
        return False

    try:
        api_key = get_secret("GEMINI_API_KEY")
        if not api_key or not GENAI_AVAILABLE:
            await _send_event(queue, "error", {"message": "Brak klucza GEMINI_API_KEY."})
            session.job_status = "error"
            session.job_error = "Brak klucza GEMINI_API_KEY."
            return

        client = genai.Client(api_key=api_key)

        # Laduj PIL images z dysku
        pil_images = []
        for sp in source_paths:
            try:
                img = PIL.Image.open(sp)
                img.load()
                pil_images.append(img)
            except Exception:
                await _send_event(queue, "warning", {"message": f"Plik {sp} uszkodzony, pominieto."})

        if not pil_images:
            await _send_event(queue, "error", {"message": "Zadne zdjecie nie zostalo wczytane."})
            session.job_status = "error"
            session.job_error = "Brak zdjec."
            return

        # --- [0] Ekstrakcja specyfikacji ---
        await _send_event(queue, "progress", {"step": 0, "total": 12, "message": "Analizuje specyfikacje..."})

        extracted = await _api_call_with_timeout(
            asyncio.to_thread(extract_spec_data, client, specyfikacja, pil_images[:4])
        )
        session.api_calls_count += 1
        session.text_gen_count += 1
        _track_cost(session, "gemini-text", COST_GEMINI_TEXT_USD)

        await _send_event(queue, "extraction", {
            "fields": {k: v for k, v in extracted.items() if v is not None}
        })
        await asyncio.sleep(RATE_LIMIT_SEC)

        # --- [0] Background Removal (rembg) ---
        session.current_phase = "dna"
        await _send_event(queue, "progress", {"step": 1, "total": 12, "message": "Usuwanie tla ze zdjec..."})
        transparent_images = []
        for img in pil_images:
            try:
                no_bg = await asyncio.to_thread(remove_background, img)
                transparent_images.append(no_bg)
            except Exception as e:
                logger.warning(f"rembg failed: {str(e)[:100]}")
                transparent_images.append(img.convert("RGBA"))

        # Zapisz transparent PNG na dysk
        for i, t_img in enumerate(transparent_images):
            t_path = job_dir / f"transparent_{i+1}.png"
            t_img.save(str(t_path))
            session.transparent_images[f"transparent_{i+1}"] = str(t_path)

        await _send_event(queue, "background_removed", {
            "count": len(transparent_images),
            "message": f"Usunieto tlo z {len(transparent_images)} zdjec",
        })

        if _check_cancel():
            await _send_event(queue, "cancelled", {"message": "Anulowano przez uzytkownika"})
            return

        # --- [1] Product DNA (Gemini TEXT) ---
        await _send_event(queue, "progress", {"step": 2, "total": 12, "message": "Analiza produktu (Product DNA)..."})
        product_dna_json = "{}"
        try:
            product_dna_json = await analyze_product_dna(client, pil_images[:2])
            session.api_calls_count += 1
            session.text_gen_count += 1
            _track_cost(session, "gemini-text", COST_GEMINI_TEXT_USD)
        except Exception as e:
            logger.error(f"[{session.job_id}] Product DNA failed: {str(e)[:200]}", exc_info=True)
            await _send_event(queue, "warning", {"message": f"Analiza produktu: {get_user_error(e)}"})

        # Zapisz DNA w sesji
        try:
            session.product_dna = json.loads(product_dna_json)
        except json.JSONDecodeError:
            session.product_dna = {}

        await _send_event(queue, "product_dna", {"dna": product_dna_json})
        await asyncio.sleep(RATE_LIMIT_SEC)

        # =====================================================================
        # FAZA 1: PACKSHOTY
        # =====================================================================
        session.current_phase = "phase1"
        generated_images = {}
        imgs_for_gen = transparent_images[:2] if transparent_images else [img.convert("RGBA") for img in pil_images[:2]]

        # --- [2a] Packshoty indywidualne (Pillow, $0) ---
        await _send_event(queue, "progress", {"step": 3, "total": 12, "message": "Tworzenie packshotow (Pillow)..."})

        packshot_gen = PillowPackshotGenerator()
        for i, t_img in enumerate(transparent_images):
            pack_img = await packshot_gen.generate_with_retry(
                prompt="packshot",
                reference_images=[t_img],
            )
            if pack_img:
                key = f"packshot_{i+1}_{timestamp}"
                img_path = job_dir / f"{key}.png"
                pack_img.save(str(img_path))
                generated_images[key] = str(img_path)
                session.approved_packshots[key] = str(img_path)

                await _send_event(queue, "image", {
                    "key": key,
                    "url": f"/api/images/{job_id}/{key}",
                    "name": f"Packshot {i+1}",
                })

        # --- [2b] Kompozyty zestawu (Gemini Flash) ---
        await _send_event(queue, "progress", {"step": 4, "total": 12, "message": "Generowanie kompozytow zestawu..."})

        # Buduj liste produktow z Product DNA
        dna_dict = session.product_dna or {}
        composite_products = []
        if dna_dict.get("nazwa"):
            composite_products.append({
                "name": dna_dict.get("nazwa", "zlew granitowy"),
                "description": dna_dict.get("opis_krotki", ""),
            })
        if dna_dict.get("akcesoria"):
            for acc in dna_dict["akcesoria"]:
                if isinstance(acc, dict):
                    composite_products.append({
                        "name": acc.get("nazwa", "akcesorium"),
                        "description": acc.get("opis", ""),
                    })
                elif isinstance(acc, str):
                    composite_products.append({"name": acc, "description": ""})
        if not composite_products:
            composite_products = [{"name": "zlew granitowy z akcesoriami", "description": specyfikacja[:200]}]

        composite_prompt = get_composite_packshot_prompt(composite_products)
        composite_chain = get_composite_generators()
        comp_img, comp_model, comp_cost = await generate_with_fallback(
            composite_chain, composite_prompt, imgs_for_gen,
        )
        if comp_img:
            session.api_calls_count += 1
            session.image_gen_count += 1
            _track_cost(session, comp_model, comp_cost)

            key = f"composite_{timestamp}"
            img_path = job_dir / f"{key}.png"
            comp_img.save(str(img_path))
            generated_images[key] = str(img_path)

            await _send_event(queue, "image", {
                "key": key,
                "url": f"/api/images/{job_id}/{key}",
                "name": f"Kompozyt zestawu ({comp_model})",
            })
        else:
            await _send_event(queue, "warning", {"message": "Kompozyt zestawu: wszystkie generatory zawiodly."})

        if _check_cancel():
            await _send_event(queue, "cancelled", {"message": "Anulowano przez uzytkownika"})
            return

        # --- BRAMKA FAZY 1 ---
        session.current_phase = "phase1_approval"
        session.phase_event = asyncio.Event()
        session.phase_approved = False
        session.phase_round = 0

        phase1_images = {k: f"/api/images/{job_id}/{k}" for k in generated_images}
        await _send_event(queue, "phase1_complete", {
            "images": phase1_images,
            "images_count": len(generated_images),
            "cost_usd": session.total_cost_usd,
            "model_costs": session.model_costs,
        })

        # Petla feedback Fazy 1
        for _round in range(MAX_FEEDBACK_ROUNDS):
            try:
                await asyncio.wait_for(session.phase_event.wait(), timeout=PHASE_TIMEOUT_SEC)
            except asyncio.TimeoutError:
                await _send_event(queue, "phase_timeout", {"phase": "phase1"})
                session.current_phase = "error"
                session.job_status = "error"
                session.job_error = "Timeout bramki Fazy 1."
                return

            if session.phase_approved:
                break

            # Feedback: regeneruj kompozyt z poprawkami
            if session.phase_round >= SOFT_WARNING_ROUNDS:
                await _send_event(queue, "soft_warning", {
                    "message": f"Runda {session.phase_round}/{MAX_FEEDBACK_ROUNDS}. Rozważ akceptację.",
                    "round": session.phase_round,
                    "max_rounds": MAX_FEEDBACK_ROUNDS,
                })

            await _send_event(queue, "progress", {
                "step": 4, "total": 12,
                "message": f"Regeneracja kompozytu (runda {session.phase_round})...",
            })

            regen_prompt = get_composite_packshot_prompt(composite_products)
            if session.phase_feedback:
                regen_prompt += f"\n\n=== USER FEEDBACK (apply these corrections) ===\n{session.phase_feedback}"
            comp_img2, comp_model2, comp_cost2 = await generate_with_fallback(
                composite_chain, regen_prompt, imgs_for_gen,
            )
            if comp_img2:
                session.api_calls_count += 1
                session.image_gen_count += 1
                _track_cost(session, comp_model2, comp_cost2)

                key = f"composite_{timestamp}"
                img_path = job_dir / f"{key}.png"
                comp_img2.save(str(img_path))
                generated_images[key] = str(img_path)

                await _send_event(queue, "image", {
                    "key": key,
                    "url": f"/api/images/{job_id}/{key}",
                    "name": f"Kompozyt zestawu v{session.phase_round} ({comp_model2})",
                })

            phase1_images = {k: f"/api/images/{job_id}/{k}" for k in generated_images}
            await _send_event(queue, "phase1_complete", {
                "images": phase1_images,
                "images_count": len(generated_images),
                "round": session.phase_round,
                "cost_usd": session.total_cost_usd,
            })

            # Reset event na kolejna runde
            session.phase_event.clear()

        if not session.phase_approved:
            # Limit rund wyczerpany, kontynuuj z aktualnym stanem
            await _send_event(queue, "warning", {
                "message": f"Wyczerpano limit rund ({MAX_FEEDBACK_ROUNDS}). Kontynuuje z aktualnymi packshotami.",
            })

        # Zapisz approved packshots
        session.approved_packshots = dict(generated_images)

        if _check_cancel():
            await _send_event(queue, "cancelled", {"message": "Anulowano przez uzytkownika"})
            return

        # =====================================================================
        # FAZA 2: LIFESTYLE
        # =====================================================================
        session.current_phase = "phase2"
        lifestyle_scenes = LIFESTYLE_SCENES
        lifestyle_generators = get_lifestyle_generators()

        for scene_idx, scene_config in enumerate(lifestyle_scenes):
            if _check_cancel():
                await _send_event(queue, "cancelled", {"message": "Anulowano przez uzytkownika"})
                return

            step_num = 5 + scene_idx
            scene_name = scene_config["name"]

            await _send_event(queue, "progress", {
                "step": step_num,
                "total": 12,
                "message": f"Generowanie: {scene_name}",
            })

            prompt = get_lifestyle_prompt_v2(scene_config, product_dna_json)
            best_score = 0
            best_img = None
            best_model = "unknown"

            for attempt in range(3):  # 1 oryginalna proba + max 2 retry
                try:
                    gen_img, gen_model, gen_cost = await generate_with_fallback(
                        lifestyle_generators, prompt, imgs_for_gen,
                    )
                    session.api_calls_count += 1
                    session.image_gen_count += 1

                    if gen_img:
                        _track_cost(session, gen_model, gen_cost)
                    else:
                        await _send_event(queue, "warning", {"message": f"{scene_name}: brak obrazu."})
                        break

                    await asyncio.sleep(RATE_LIMIT_SEC)

                    # Self-check
                    score, differences, corrections = await run_selfcheck(client, pil_images[0], gen_img, product_dna_json)
                    session.api_calls_count += 1
                    session.text_gen_count += 1
                    _track_cost(session, "gemini-text", COST_GEMINI_TEXT_USD)

                    await _send_event(queue, "selfcheck", {
                        "scene": scene_name,
                        "attempt": attempt + 1,
                        "score": score,
                        "differences": differences,
                    })

                    if score >= best_score:
                        best_score = score
                        best_img = gen_img
                        best_model = gen_model

                    if score >= 8:
                        break  # Jakosc OK (prog z RETRY_THRESHOLD w config)

                    if attempt < 2:
                        await _send_event(queue, "retry", {
                            "scene": scene_name,
                            "attempt": attempt + 2,
                            "corrections": corrections,
                        })
                        prompt = get_lifestyle_prompt_v2(scene_config, product_dna_json, corrections=corrections)
                        await asyncio.sleep(RATE_LIMIT_SEC)

                except Exception as e:
                    logger.error(f"[{session.job_id}] Lifestyle failed: {scene_name} - {str(e)[:200]}", exc_info=True)
                    await _send_event(queue, "warning", {"message": f"{scene_name}: {get_user_error(e)}"})
                    break

            # Zapisz najlepsze zdjecie
            if best_img:
                key = f"lifestyle_{scene_idx+1}_{timestamp}"
                img_path = job_dir / f"{key}.png"
                best_img.save(str(img_path))
                generated_images[key] = str(img_path)

                await _send_event(queue, "image", {
                    "key": key,
                    "url": f"/api/images/{job_id}/{key}",
                    "name": f"{scene_name} (score: {best_score}/10, {best_model})",
                })

            await asyncio.sleep(RATE_LIMIT_SEC)

        # --- BRAMKA FAZY 2 ---
        session.current_phase = "phase2_approval"
        session.phase_event = asyncio.Event()
        session.phase_approved = False
        session.phase_round = 0

        all_images_urls = {k: f"/api/images/{job_id}/{k}" for k in generated_images}
        await _send_event(queue, "phase2_complete", {
            "images": all_images_urls,
            "images_count": len(generated_images),
            "cost_usd": session.total_cost_usd,
            "model_costs": session.model_costs,
        })

        # Petla feedback Fazy 2 (regeneracja konkretnych scen)
        for _round in range(MAX_FEEDBACK_ROUNDS):
            try:
                await asyncio.wait_for(session.phase_event.wait(), timeout=PHASE_TIMEOUT_SEC)
            except asyncio.TimeoutError:
                await _send_event(queue, "phase_timeout", {"phase": "phase2"})
                session.current_phase = "error"
                session.job_status = "error"
                session.job_error = "Timeout bramki Fazy 2."
                return

            if session.phase_approved:
                break

            if session.phase_round >= SOFT_WARNING_ROUNDS:
                await _send_event(queue, "soft_warning", {
                    "message": f"Runda {session.phase_round}/{MAX_FEEDBACK_ROUNDS}. Rozważ akceptację.",
                    "round": session.phase_round,
                    "max_rounds": MAX_FEEDBACK_ROUNDS,
                })

            # Regeneruj najslabsza scene z feedback
            await _send_event(queue, "progress", {
                "step": 10, "total": 12,
                "message": f"Regeneracja lifestyle (runda {session.phase_round})...",
            })

            # Regeneruj scene 0 (lub parse feedback w przyszlosci)
            regen_scene = lifestyle_scenes[0]
            regen_prompt = get_lifestyle_prompt_v2(regen_scene, product_dna_json, corrections=session.phase_feedback)
            regen_img, regen_model, regen_cost = await generate_with_fallback(
                lifestyle_generators, regen_prompt, imgs_for_gen,
            )
            if regen_img:
                session.api_calls_count += 1
                session.image_gen_count += 1
                _track_cost(session, regen_model, regen_cost)

                key = f"lifestyle_regen_{session.phase_round}_{timestamp}"
                img_path = job_dir / f"{key}.png"
                regen_img.save(str(img_path))
                generated_images[key] = str(img_path)

                await _send_event(queue, "image", {
                    "key": key,
                    "url": f"/api/images/{job_id}/{key}",
                    "name": f"Lifestyle regen v{session.phase_round} ({regen_model})",
                })

            all_images_urls = {k: f"/api/images/{job_id}/{k}" for k in generated_images}
            await _send_event(queue, "phase2_complete", {
                "images": all_images_urls,
                "images_count": len(generated_images),
                "round": session.phase_round,
                "cost_usd": session.total_cost_usd,
            })

            session.phase_event.clear()

        if not session.phase_approved:
            await _send_event(queue, "warning", {
                "message": f"Wyczerpano limit rund ({MAX_FEEDBACK_ROUNDS}). Kontynuuje do opisu.",
            })

        # =====================================================================
        # FINALIZACJA: Opis B2C
        # =====================================================================
        session.current_phase = "finalizing"
        await _send_event(queue, "progress", {
            "step": 11,
            "total": 12,
            "message": "Generuje opis Allegro...",
        })

        desc_text = ""
        try:
            desc_prompt = generate_description_prompt(
                specyfikacja, kategoria, catalog_key,
                kolor_zlew=kolor_zlew, kolor_bateria=kolor_bateria,
                kolor_syfon=kolor_syfon, kolor_dozownik=kolor_dozownik,
            )
            desc_response = await _api_call_with_timeout(asyncio.to_thread(
                lambda: client.models.generate_content(
                    model=MODEL,
                    contents=[desc_prompt] + pil_images[:4],
                    config=types.GenerateContentConfig(response_modalities=["TEXT"]),
                )
            ))
            if desc_response.candidates and desc_response.parts:
                for part in desc_response.parts:
                    if part.text:
                        desc_text += part.text
                session.text_gen_count += 1
                session.api_calls_count += 1
                _track_cost(session, "gemini-text", COST_GEMINI_TEXT_USD)
            else:
                await _send_event(queue, "warning", {
                    "message": "Opis zablokowany przez filtr bezpieczenstwa.",
                })
        except Exception as e:
            logger.error(f"[{session.job_id}] Description failed: {str(e)[:200]}", exc_info=True)
            await _send_event(queue, "warning", {
                "message": f"Opis: {get_user_error(e)}",
            })

        # Parsowanie sekcji
        sections = parse_description_sections(desc_text)

        if desc_text:
            logger.info(f"Description generated: {sections.get('tytul', 'N/A')[:50]}")

        # Ban list check
        banned_found = []
        if desc_text:
            banned_found = check_ban_list(desc_text)

        # Rename keys na slug tytulu
        if sections.get("tytul"):
            slug = re.sub(r'[^\w\s-]', '', sections["tytul"][:50]).strip().replace(' ', '-')
            renamed = {}
            for key, path in generated_images.items():
                prefix = key.rsplit("_", 1)[0]
                new_key = f"{slug}_{prefix}"
                old_p = Path(path)
                new_p = old_p.parent / f"{new_key}.png"
                try:
                    old_p.rename(new_p)
                    renamed[new_key] = str(new_p)
                except OSError:
                    renamed[key] = path
            generated_images = renamed

        # Dodaj oryginaly
        for i, sp in enumerate(source_paths):
            orig_key = f"original_{i+1}"
            generated_images[orig_key] = sp

        # Zapisz wyniki w sesji
        session.results_images = generated_images
        session.results_sections = sections
        session.results_desc_raw = desc_text

        # Zapisz do historii
        await asyncio.to_thread(
            save_generation,
            title=sections.get("tytul", ""),
            sku=sections.get("sku", ""),
            catalog=catalog_key,
            kategoria=kategoria,
            timestamp=timestamp,
            images_count=len(generated_images),
        )

        # Auto-save szkicu
        try:
            grafiki_b64 = {}
            for key, path in generated_images.items():
                if key.startswith("original_"):
                    continue
                fp = Path(path)
                if fp.exists():
                    grafiki_b64[key] = base64.b64encode(fp.read_bytes()).decode()

            auto_data = {
                "kategoria": f"{catalog_key} / {kategoria}",
                "kolory": session.last_kolory,
                "grafiki": grafiki_b64,
                "opis": desc_text,
                "specyfikacja": specyfikacja,
                "tytul": sections.get("tytul", ""),
                "sku": sections.get("sku", ""),
                "bullets": sections.get("bullets", ""),
            }
            auto_id = await asyncio.to_thread(save_auction, auto_data, "szkic")
            session.last_auto_draft_id = auto_id
        except Exception:
            pass  # Auto-save nie blokuje flow

        # --- Event complete ---
        gen_count = len([k for k in generated_images if not k.startswith("original_")])
        images_urls = {k: f"/api/images/{job_id}/{k}" for k in generated_images}

        session.current_phase = "done"
        session.job_status = "done"
        await _send_event(queue, "complete", {
            "images_count": gen_count,
            "has_description": bool(desc_text),
            "sections": sections,
            "images": images_urls,
            "timestamp": timestamp,
            "cost_pln": round(_session_cost_pln(session), 2),
            "cost_usd": session.total_cost_usd,
            "model_costs": session.model_costs,
            "banned_phrases": banned_found,
            "extraction": {k: v for k, v in extracted.items() if v is not None},
        })

    except Exception as e:
        logger.error(f"[{session.job_id}] Generation failed: {type(e).__name__}: {str(e)[:200]}", exc_info=True)
        session.current_phase = "error"
        session.job_status = "error"
        session.job_error = get_user_error(e)
        await _send_event(queue, "error", {"message": get_user_error(e)})

    finally:
        # Cleanup PIL images
        for _img in pil_images:
            try:
                _img.close()
            except Exception:
                pass
        for _img in transparent_images:
            try:
                _img.close()
            except Exception:
                pass
        # Signal koniec streamu
        if queue is not None:
            await queue.put(None)


# ---------------------------------------------------------------------------
# Startup Validation
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup_validation():
    """Weryfikacja kluczy API przy starcie serwera."""
    logger.info("=== Startup Validation ===")
    logger.info(f"GEMINI_API_KEY: {'configured' if GEMINI_API_KEY else 'MISSING'}")
    logger.info(f"FAL_AI_API_KEY: {'configured' if FAL_AI_API_KEY else 'MISSING'}")
    logger.info(f"OPENAI_API_KEY: {'configured' if OPENAI_API_KEY else 'MISSING'}")
    logger.info(f"REMBG_MODEL: {REMBG_MODEL}")
    logger.info(f"CORS_ORIGINS: {CORS_ORIGINS}")
    if not APP_PASSWORD:
        logger.critical("APP_PASSWORD not set! Auth will be required.")


# ---------------------------------------------------------------------------
# Static files (MUSI byc OSTATNIE - catch-all)
# ---------------------------------------------------------------------------

# React frontend (Vite build) pod /app/
_frontend_dist = Path(__file__).parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/app", StaticFiles(directory=str(_frontend_dist), html=True), name="react-app")

# Legacy static UI (catch-all, musi byc po /app)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
