"""
Abstrakcja generatorow obrazow - Pipeline v3.0.
ABC + implementacje per model + normalize_output + fallback chain.
"""

import asyncio
import base64
import io
import logging
import os
import time
from abc import ABC, abstractmethod

import PIL.Image

from config import (
    GEMINI_API_KEY, GEMINI_FLASH_IMAGE_MODEL, GEMINI_PRO_IMAGE_MODEL,
    OPENAI_API_KEY, OPENAI_IMAGE_MODEL, FAL_AI_API_KEY,
    KONTEXT_MAX_MODEL, KONTEXT_PRO_MODEL,
    FLUX_2_LORA_MODEL, FLUX_2_PRO_EDIT_MODEL, KLING_O3_MODEL,
    LORA_MODEL_PATH, LORA_TRIGGER_WORD, LORA_WEIGHT,
    COST_KONTEXT_MAX_IMAGE_USD, COST_KONTEXT_PRO_IMAGE_USD,
    COST_FLUX_2_LORA_IMAGE_USD, COST_FLUX_2_PRO_EDIT_IMAGE_USD,
    COST_KLING_O3_IMAGE_USD, COST_GEMINI_FLASH_IMAGE_USD,
    COST_GEMINI_PRO_IMAGE_USD, COST_GPT_IMAGE_USD,
    COST_LORA_IMAGE_USD,
    PACKSHOT_SIZE, LIFESTYLE_SIZE, COMPOSITE_SIZE,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_output(img: PIL.Image.Image, target_size: tuple[int, int]) -> PIL.Image.Image:
    """Resize + crop do target_size. Zachowuje proporcje, cropuje centrum."""
    if img.mode == "RGBA":
        bg = PIL.Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg

    tw, th = target_size
    target_ratio = tw / th
    iw, ih = img.size
    img_ratio = iw / ih

    if img_ratio > target_ratio:
        new_h = ih
        new_w = int(ih * target_ratio)
    else:
        new_w = iw
        new_h = int(iw / target_ratio)

    left = (iw - new_w) // 2
    top = (ih - new_h) // 2
    img = img.crop((left, top, left + new_w, top + new_h))
    img = img.resize(target_size, PIL.Image.LANCZOS)
    return img


def _extract_image_from_gemini_response(response) -> PIL.Image.Image | None:
    """Wyciaga PIL Image z odpowiedzi Gemini."""
    if not response or not response.parts:
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


# ---------------------------------------------------------------------------
# ABC
# ---------------------------------------------------------------------------

class ImageGenerator(ABC):
    """Bazowy interfejs dla wszystkich generatorow obrazow."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        reference_images: list[PIL.Image.Image] | None = None,
        target_size: tuple[int, int] = LIFESTYLE_SIZE,
    ) -> PIL.Image.Image | None:
        ...

    @abstractmethod
    def cost_per_image(self) -> float:
        ...

    @abstractmethod
    def name(self) -> str:
        ...

    async def health_check(self) -> bool:
        """Sprawdza dostepnosc providera. Default: True."""
        return True

    def max_reference_images(self) -> int:
        return 0

    async def generate_with_retry(
        self,
        prompt: str,
        reference_images: list[PIL.Image.Image] | None = None,
        target_size: tuple[int, int] = LIFESTYLE_SIZE,
        max_retries: int = 3,
    ) -> PIL.Image.Image | None:
        """Generate z exponential backoff. Retry WEWNATRZ generatora."""
        for attempt in range(1, max_retries + 1):
            try:
                result = await self.generate(prompt, reference_images, target_size)
                if result is not None:
                    return normalize_output(result, target_size)
                if attempt < max_retries:
                    logger.warning(
                        f"{self.name()} zwrocil None, retry {attempt}/{max_retries}"
                    )
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                err = str(e)
                retryable = any(
                    code in err for code in ["429", "500", "503", "RESOURCE_EXHAUSTED"]
                )
                if attempt < max_retries and retryable:
                    wait = 5 * attempt
                    logger.warning(
                        f"{self.name()} error retry {attempt}/{max_retries}: "
                        f"{err[:120]}, wait {wait}s"
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"{self.name()} final error: {err[:200]}")
                    return None
        return None


# ---------------------------------------------------------------------------
# Gemini Flash Image (Nano Banana 2)
# ---------------------------------------------------------------------------

class GeminiFlashImageGenerator(ImageGenerator):
    """Gemini 3.1 Flash Image - kompozyty zestawu + lifestyle fallback.
    Do 10 zdjec referencyjnych, Thinking mode, native API."""

    def __init__(self, thinking_level: str | None = "HIGH"):
        self._thinking_level = thinking_level
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=GEMINI_API_KEY)
        return self._client

    async def generate(
        self,
        prompt: str,
        reference_images: list[PIL.Image.Image] | None = None,
        target_size: tuple[int, int] = LIFESTYLE_SIZE,
    ) -> PIL.Image.Image | None:
        from google.genai import types

        client = self._get_client()
        contents: list = [prompt]
        if reference_images:
            contents.extend(reference_images[:10])

        config_kwargs = {
            "response_modalities": ["IMAGE", "TEXT"],
        }
        if self._thinking_level:
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level=self._thinking_level
            )

        gen_config = types.GenerateContentConfig(**config_kwargs)

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=GEMINI_FLASH_IMAGE_MODEL,
                contents=contents,
                config=gen_config,
            ),
        )
        return _extract_image_from_gemini_response(response)

    def cost_per_image(self) -> float:
        return COST_GEMINI_FLASH_IMAGE_USD

    def name(self) -> str:
        return "Gemini 3.1 Flash Image"

    def max_reference_images(self) -> int:
        return 10

    async def health_check(self) -> bool:
        return bool(GEMINI_API_KEY)


# ---------------------------------------------------------------------------
# Gemini Pro Image (Nano Banana Pro) - legacy + high quality
# ---------------------------------------------------------------------------

class GeminiProImageGenerator(ImageGenerator):
    """Gemini 3 Pro Image - legacy generator, zachowany dla kompatybilnosci."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=GEMINI_API_KEY)
        return self._client

    async def generate(
        self,
        prompt: str,
        reference_images: list[PIL.Image.Image] | None = None,
        target_size: tuple[int, int] = LIFESTYLE_SIZE,
    ) -> PIL.Image.Image | None:
        from google.genai import types

        client = self._get_client()
        contents: list = [prompt]
        if reference_images:
            contents.extend(reference_images[:6])

        gen_config = types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
            image_config=types.ImageConfig(imageSize="2K"),
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=GEMINI_PRO_IMAGE_MODEL,
                contents=contents,
                config=gen_config,
            ),
        )
        return _extract_image_from_gemini_response(response)

    def cost_per_image(self) -> float:
        return COST_GEMINI_PRO_IMAGE_USD

    def name(self) -> str:
        return "Gemini 3 Pro Image"

    def max_reference_images(self) -> int:
        return 6

    async def health_check(self) -> bool:
        return bool(GEMINI_API_KEY)


# ---------------------------------------------------------------------------
# Pillow Packshot (lokalne, $0)
# ---------------------------------------------------------------------------

class PillowPackshotGenerator(ImageGenerator):
    """Lokalne packshoty na bialym tle z cieniem kontaktowym. Koszt $0."""

    async def generate(
        self,
        prompt: str,
        reference_images: list[PIL.Image.Image] | None = None,
        target_size: tuple[int, int] = PACKSHOT_SIZE,
    ) -> PIL.Image.Image | None:
        if not reference_images:
            return None

        tw, th = target_size
        canvas = PIL.Image.new("RGB", (tw, th), (255, 255, 255))

        if len(reference_images) == 1:
            img = reference_images[0]
            img_ratio = img.width / img.height
            target_ratio = tw / th

            if img_ratio > target_ratio:
                new_w = int(tw * 0.85)
                new_h = int(new_w / img_ratio)
            else:
                new_h = int(th * 0.85)
                new_w = int(new_h * img_ratio)

            resized = img.resize((new_w, new_h), PIL.Image.LANCZOS)
            x = (tw - new_w) // 2
            y = (th - new_h) // 2

            if resized.mode == "RGBA":
                canvas.paste(resized, (x, y), resized.split()[3])
            else:
                canvas.paste(resized, (x, y))
        else:
            n = len(reference_images)
            slot_w = tw // min(n, 3)
            for i, img in enumerate(reference_images[:3]):
                img_ratio = img.width / img.height
                new_h = int(th * 0.75)
                new_w = int(new_h * img_ratio)
                if new_w > slot_w * 0.9:
                    new_w = int(slot_w * 0.9)
                    new_h = int(new_w / img_ratio)

                resized = img.resize((new_w, new_h), PIL.Image.LANCZOS)
                x = i * slot_w + (slot_w - new_w) // 2
                y = (th - new_h) // 2

                if resized.mode == "RGBA":
                    canvas.paste(resized, (x, y), resized.split()[3])
                else:
                    canvas.paste(resized, (x, y))

        return canvas

    def cost_per_image(self) -> float:
        return 0.0

    def name(self) -> str:
        return "Pillow Packshot"

    def max_reference_images(self) -> int:
        return 10


# ---------------------------------------------------------------------------
# Helpers: FAL.AI
# ---------------------------------------------------------------------------

def _download_image_from_url(url: str) -> PIL.Image.Image | None:
    """Pobiera obraz z URL i zwraca PIL Image."""
    try:
        import requests
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        img = PIL.Image.open(io.BytesIO(resp.content))
        img.load()
        return img
    except Exception as e:
        logger.error(f"Blad pobierania obrazu z {url[:80]}: {e}")
        return None


def _pil_to_base64_uri(img: PIL.Image.Image) -> str:
    """Konwertuje PIL Image na base64 data URI (JPEG)."""
    if img.mode == "RGBA":
        bg = PIL.Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


# ---------------------------------------------------------------------------
# Kontext Max via FAL.AI (PRIMARY lifestyle)
# ---------------------------------------------------------------------------

class KontextMaxGenerator(ImageGenerator):
    """Kontext Max - image editing. Wstawia produkt (transparent PNG) w scene.
    Zachowuje geometrie produktu 1:1. $0.08 flat."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            os.environ["FAL_KEY"] = FAL_AI_API_KEY
            import fal_client
            self._client = fal_client
        return self._client

    async def generate(self, prompt, reference_images=None, target_size=LIFESTYLE_SIZE):
        if not reference_images:
            logger.warning("KontextMax: brak reference image (produkt PNG)")
            return None

        client = self._get_client()
        product_uri = _pil_to_base64_uri(reference_images[0])

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.subscribe(
                KONTEXT_MAX_MODEL,
                arguments={
                    "prompt": prompt,
                    "image_url": product_uri,
                    "image_size": {"width": target_size[0], "height": target_size[1]},
                    "num_images": 1,
                    "output_format": "jpeg",
                },
            ),
        )
        url = result["images"][0]["url"]
        return _download_image_from_url(url)

    def cost_per_image(self): return COST_KONTEXT_MAX_IMAGE_USD
    def name(self): return "Kontext Max"
    def max_reference_images(self): return 1
    async def health_check(self): return bool(FAL_AI_API_KEY)


# ---------------------------------------------------------------------------
# Flux 2 Pro Edit via FAL.AI (composite fallback)
# ---------------------------------------------------------------------------

class Flux2ProEditGenerator(ImageGenerator):
    """Flux 2 Pro Edit - multi-ref z @ syntax. Do 9 referencji.
    $0.03/MP first + $0.015/MP additional."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            os.environ["FAL_KEY"] = FAL_AI_API_KEY
            import fal_client
            self._client = fal_client
        return self._client

    async def generate(self, prompt, reference_images=None, target_size=COMPOSITE_SIZE):
        client = self._get_client()

        arguments = {
            "prompt": prompt,
            "image_size": {"width": target_size[0], "height": target_size[1]},
            "num_images": 1,
            "output_format": "jpeg",
        }

        if reference_images:
            image_urls = [_pil_to_base64_uri(img) for img in reference_images[:9]]
            arguments["image_urls"] = image_urls

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.subscribe(
                FLUX_2_PRO_EDIT_MODEL,
                arguments=arguments,
            ),
        )
        url = result["images"][0]["url"]
        return _download_image_from_url(url)

    def cost_per_image(self): return COST_FLUX_2_PRO_EDIT_IMAGE_USD
    def name(self): return "Flux 2 Pro Edit"
    def max_reference_images(self): return 9
    async def health_check(self): return bool(FAL_AI_API_KEY)


# ---------------------------------------------------------------------------
# Kling Image O3 via FAL.AI (composite fallback 2)
# ---------------------------------------------------------------------------

class KlingO3Generator(ImageGenerator):
    """Kling Image O3 - multi-ref z @ syntax. Do 10 referencji.
    $0.028 za 2K."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            os.environ["FAL_KEY"] = FAL_AI_API_KEY
            import fal_client
            self._client = fal_client
        return self._client

    async def generate(self, prompt, reference_images=None, target_size=COMPOSITE_SIZE):
        client = self._get_client()
        tw, th = target_size

        ratio = tw / th
        if abs(ratio - 1.0) < 0.1:
            aspect = "1:1"
        elif abs(ratio - 4/3) < 0.1:
            aspect = "4:3"
        elif abs(ratio - 3/4) < 0.1:
            aspect = "3:4"
        elif abs(ratio - 16/9) < 0.1:
            aspect = "16:9"
        else:
            aspect = "1:1"

        arguments = {
            "prompt": prompt,
            "aspect_ratio": aspect,
            "num_images": 1,
        }

        if reference_images:
            image_urls = [_pil_to_base64_uri(img) for img in reference_images[:10]]
            arguments["image_urls"] = image_urls

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.subscribe(
                KLING_O3_MODEL,
                arguments=arguments,
            ),
        )
        url = result["images"][0]["url"]
        return _download_image_from_url(url)

    def cost_per_image(self): return COST_KLING_O3_IMAGE_USD
    def name(self): return "Kling Image O3"
    def max_reference_images(self): return 10
    async def health_check(self): return bool(FAL_AI_API_KEY)


# ---------------------------------------------------------------------------
# GPT Image 1.5 via OpenAI (ostatni fallback lifestyle)
# ---------------------------------------------------------------------------

class GPTImage15Generator(ImageGenerator):
    """GPT Image 1.5 - #1 LMArena. Do 16 referencji, input_fidelity:high.
    $0.133 high 1024x1024, $0.200 high landscape."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=OPENAI_API_KEY)
        return self._client

    async def generate(self, prompt, reference_images=None, target_size=LIFESTYLE_SIZE):
        client = self._get_client()
        tw, th = target_size

        if tw > th:
            size = "1536x1024"
        elif th > tw:
            size = "1024x1536"
        else:
            size = "1024x1024"

        loop = asyncio.get_event_loop()

        if reference_images:
            product_img = reference_images[0]
            buf = io.BytesIO()
            if product_img.mode != "RGBA":
                product_img = product_img.convert("RGBA")
            product_img.save(buf, format="PNG")
            buf.seek(0)

            response = await loop.run_in_executor(
                None,
                lambda: client.images.edit(
                    model=OPENAI_IMAGE_MODEL,
                    image=buf,
                    prompt=prompt,
                    size=size,
                    n=1,
                ),
            )
        else:
            response = await loop.run_in_executor(
                None,
                lambda: client.images.generate(
                    model=OPENAI_IMAGE_MODEL,
                    prompt=prompt,
                    size=size,
                    quality="high",
                    n=1,
                ),
            )

        image_data = response.data[0]
        if hasattr(image_data, "b64_json") and image_data.b64_json:
            img_bytes = base64.b64decode(image_data.b64_json)
            img = PIL.Image.open(io.BytesIO(img_bytes))
            img.load()
            return img
        elif hasattr(image_data, "url") and image_data.url:
            return _download_image_from_url(image_data.url)
        return None

    def cost_per_image(self): return COST_GPT_IMAGE_USD
    def name(self): return "GPT Image 1.5"
    def max_reference_images(self): return 16
    async def health_check(self): return bool(OPENAI_API_KEY)


# ---------------------------------------------------------------------------
# Flux 2 LoRA via FAL.AI
# ---------------------------------------------------------------------------

class Flux2LoRAGenerator(ImageGenerator):
    """Flux 2 LoRA - wytrenowane LoRA via FAL.AI. Max 3 LoRA jednoczesnie.
    $0.021/MP. Multi-ref z @ syntax."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            os.environ["FAL_KEY"] = FAL_AI_API_KEY
            import fal_client
            self._client = fal_client
        return self._client

    def _get_lora_url(self) -> str:
        """Pobierz URL LoRA z config lub rejestru wersji."""
        import config
        if config.LORA_MODEL_PATH:
            return config.LORA_MODEL_PATH
        from lora_training import LoRATrainer
        url = LoRATrainer().get_active_lora_url()
        return url or ""

    async def generate(self, prompt, reference_images=None, target_size=LIFESTYLE_SIZE):
        lora_url = self._get_lora_url()
        if not lora_url:
            logger.warning("Flux2LoRA: brak LoRA URL (config + rejestr), LoRA nie wytrenowane")
            return None

        client = self._get_client()

        arguments = {
            "prompt": prompt,
            "image_size": {"width": target_size[0], "height": target_size[1]},
            "num_images": 1,
            "output_format": "jpeg",
            "num_inference_steps": 28,
            "guidance_scale": 2.5,
            "loras": [{"path": lora_url, "scale": LORA_WEIGHT}],
        }

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.subscribe(
                FLUX_2_LORA_MODEL,
                arguments=arguments,
            ),
        )
        url = result["images"][0]["url"]
        return _download_image_from_url(url)

    def cost_per_image(self): return COST_FLUX_2_LORA_IMAGE_USD
    def name(self): return "Flux 2 LoRA"
    def max_reference_images(self): return 3
    async def health_check(self): return bool(FAL_AI_API_KEY and self._get_lora_url())


# ---------------------------------------------------------------------------
# Fallback chain
# ---------------------------------------------------------------------------

LIFESTYLE_CHAIN: list[type[ImageGenerator]] = [
    KontextMaxGenerator,
    Flux2LoRAGenerator,
    GeminiFlashImageGenerator,
    GPTImage15Generator,
]

COMPOSITE_CHAIN: list[type[ImageGenerator]] = [
    GeminiFlashImageGenerator,
    Flux2ProEditGenerator,
    KlingO3Generator,
    PillowPackshotGenerator,
]


async def generate_with_fallback(
    chain: list[ImageGenerator],
    prompt: str,
    reference_images: list[PIL.Image.Image] | None = None,
    target_size: tuple[int, int] = LIFESTYLE_SIZE,
) -> tuple[PIL.Image.Image | None, str, float]:
    """Probuje generatory z listy po kolei. Zwraca (image, model_name, cost)."""
    for gen in chain:
        healthy = await gen.health_check()
        if not healthy:
            logger.warning(f"Fallback skip {gen.name()}: health check failed")
            continue

        logger.info(f"Trying generator: {gen.name()}")
        result = await gen.generate_with_retry(
            prompt, reference_images, target_size, max_retries=2
        )
        if result is not None:
            return result, gen.name(), gen.cost_per_image()

        logger.warning(f"Fallback: {gen.name()} failed, trying next")

    logger.error("All generators in chain failed")
    return None, "none", 0.0


def get_lifestyle_generators() -> list[ImageGenerator]:
    """Zwraca instancje generatorow lifestyle (aktualnie dostepnych)."""
    gens = []
    gens.append(KontextMaxGenerator())
    gens.append(Flux2LoRAGenerator())
    gens.append(GeminiFlashImageGenerator(thinking_level="HIGH"))
    gens.append(GPTImage15Generator())
    return gens


def get_composite_generators() -> list[ImageGenerator]:
    """Zwraca instancje generatorow kompozytow (aktualnie dostepnych)."""
    gens = []
    gens.append(GeminiFlashImageGenerator(thinking_level="HIGH"))
    gens.append(Flux2ProEditGenerator())
    gens.append(KlingO3Generator())
    gens.append(PillowPackshotGenerator())
    return gens


async def get_provider_status() -> dict:
    """Health check wszystkich providerow."""
    providers = {
        "gemini": {
            "configured": bool(GEMINI_API_KEY),
            "models": [GEMINI_FLASH_IMAGE_MODEL, GEMINI_PRO_IMAGE_MODEL],
        },
        "fal_ai": {
            "configured": bool(FAL_AI_API_KEY),
            "models": [KONTEXT_MAX_MODEL, FLUX_2_PRO_EDIT_MODEL, FLUX_2_LORA_MODEL, KLING_O3_MODEL],
        },
        "openai": {
            "configured": bool(OPENAI_API_KEY),
            "models": [OPENAI_IMAGE_MODEL],
        },
    }

    for name, info in providers.items():
        info["status"] = "active" if info["configured"] else "missing_key"

    return providers
