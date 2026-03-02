"""
Konfiguracja centralna Pipeline v4.3.
Stałe, modele, koszty, rozdzielczości, safeguards.
"""
import os
from dotenv import load_dotenv
load_dotenv()


def get_secret(key, default=""):
    """Pobiera secret ze zmiennych środowiskowych."""
    return os.environ.get(key, default)


# --- API Keys ---
GEMINI_API_KEY = get_secret("GEMINI_API_KEY", "")
OPENAI_API_KEY = get_secret("OPENAI_API_KEY", "")
FAL_AI_API_KEY = get_secret("FAL_AI_API_KEY", "")
APP_PASSWORD = get_secret("APP_PASSWORD", "")

# --- Modele Gemini ---
MODEL = get_secret("GEMINI_MODEL", "gemini-3-pro-image-preview")
GEMINI_TEXT_MODEL = get_secret("GEMINI_TEXT_MODEL", "gemini-3-pro")
GEMINI_FLASH_IMAGE_MODEL = get_secret(
    "GEMINI_FLASH_IMAGE_MODEL", "gemini-3.1-flash-image-preview"
)
GEMINI_PRO_IMAGE_MODEL = get_secret(
    "GEMINI_PRO_IMAGE_MODEL", "gemini-3-pro-image-preview"
)

# --- Modele obrazów ---
OPENAI_IMAGE_MODEL = get_secret("OPENAI_IMAGE_MODEL", "gpt-image-1.5")
KONTEXT_MAX_MODEL = "fal-ai/flux-pro/kontext/max"
KONTEXT_PRO_MODEL = "fal-ai/flux-pro/kontext"
FLUX_2_LORA_MODEL = "fal-ai/flux-2/lora"
FLUX_2_PRO_EDIT_MODEL = "fal-ai/flux-2-pro/edit"
KLING_O3_MODEL = "fal-ai/kling-image/o3/text-to-image"
FLUX_2_TRAINER_MODEL = "fal-ai/flux-2-trainer"
IMAGE_MODEL_PRIMARY = "kontext-max"
IMAGE_MODEL_COMPOSITE = "gemini-flash-image"
IMAGE_MODEL_COMPOSITE_FALLBACK = "flux-2-pro-edit"
IMAGE_MODEL_FALLBACK_1 = "flux-2-lora"
IMAGE_MODEL_FALLBACK_2 = "gemini-flash-image"
IMAGE_MODEL_FALLBACK_3 = "gemini-pro-image"

# --- LoRA ---
LORA_MODEL_PATH = get_secret("LORA_MODEL_PATH", "")
LORA_TRIGGER_WORD = "granite_sink_premium"
LORA_WEIGHT = 1.0

# --- LoRA Training ---
LORA_TRAINING_STEPS = 1000
LORA_MIN_IMAGES = 9
LORA_TRAINING_DIR = "training"

# --- Koszty per model (USD, research luty 2026) ---
COST_KONTEXT_MAX_IMAGE_USD = 0.08
COST_KONTEXT_PRO_IMAGE_USD = 0.04
COST_FLUX_2_LORA_IMAGE_USD = 0.063  # ~3MP @ $0.021/MP
COST_FLUX_2_PRO_EDIT_IMAGE_USD = 0.075  # ~4MP @ $0.03/MP first + $0.015 addl
COST_KLING_O3_IMAGE_USD = 0.028
COST_GEMINI_FLASH_IMAGE_USD = 0.067
COST_GEMINI_PRO_IMAGE_USD = 0.134
COST_GPT_IMAGE_USD = 0.133  # gpt-image-1.5 high 1024x1024
COST_LORA_IMAGE_USD = 0.063  # flux-2/lora z LoRA weights
COST_GEMINI_TEXT_USD = 0.02
COST_LORA_TRAINING_PER_STEP_USD = 0.008
USD_TO_PLN = 3.57

# --- Rozdzielczości (Allegro-optimized) ---
PACKSHOT_SIZE = (2000, 2000)
LIFESTYLE_SIZE = (2000, 1500)
COMPOSITE_SIZE = (2000, 2000)

# --- Pipeline ---
REMBG_MODEL = "birefnet-general"
PHASE_TIMEOUT_SEC = 1800
MAX_FEEDBACK_ROUNDS = 8
SOFT_WARNING_ROUNDS = 5
RETRY_THRESHOLD = 8
MAX_RETRIES = 2
MAX_API_CALLS_PER_SESSION = 50

# --- Batch safeguards ---
BATCH_COST_LIMIT_USD = 500.0
BATCH_RATE_LIMIT_SEC = 5
PRODUCT_TIMEOUT_SEC = 300

# --- Security ---
CORS_ORIGINS = [
    "http://localhost:8765",
    "http://127.0.0.1:8765",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
PROD_DOMAIN = get_secret("PROD_DOMAIN", "")
if PROD_DOMAIN:
    CORS_ORIGINS.append(PROD_DOMAIN)

MAX_UPLOAD_SIZE_MB = 10
MAX_IMAGES_PER_SESSION = 20
MAX_CONCURRENT_SESSIONS = 5
MAX_FEEDBACK_LENGTH = 500

# --- Allowed MIME magic bytes ---
ALLOWED_IMAGE_MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"RIFF": "image/webp",
}
