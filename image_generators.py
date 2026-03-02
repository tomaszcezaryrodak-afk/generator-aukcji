"""
Abstrakcja generatorów obrazów - Pipeline v4.3.
ABC + implementacje per model + normalize_output + fallback chain.
"""

import asyncio
import base64
import io
import logging
import os
import random
import time
from collections import deque
from abc import ABC, abstractmethod
from typing import Callable

import PIL.Image

from config import (
    GEMINI_API_KEY, GEMINI_FLASH_IMAGE_MODEL, GEMINI_PRO_IMAGE_MODEL,
    OPENAI_API_KEY, OPENAI_IMAGE_MODEL, FAL_AI_API_KEY,
    KONTEXT_MAX_MODEL, KONTEXT_PRO_MODEL,
    FLUX_2_LORA_MODEL, FLUX_2_LORA_EDIT_MODEL, FLUX_2_PRO_EDIT_MODEL, KLING_O3_MODEL,
    LORA_MODEL_PATH, LORA_TRIGGER_WORD, LORA_WEIGHT,
    COST_KONTEXT_MAX_IMAGE_USD, COST_KONTEXT_PRO_IMAGE_USD,
    COST_FLUX_2_LORA_IMAGE_USD, COST_FLUX_2_PRO_EDIT_IMAGE_USD,
    COST_KLING_O3_IMAGE_USD, COST_GEMINI_FLASH_IMAGE_USD,
    COST_GEMINI_PRO_IMAGE_USD, COST_GPT_IMAGE_USD,
    COST_LORA_IMAGE_USD,
    LORA_PRIMARY_ENABLED, LORA_EDIT_ENABLED,
    PACKSHOT_SIZE, LIFESTYLE_SIZE, COMPOSITE_SIZE,
)

logger = logging.getLogger(__name__)

# Timeout na FAL.AI subscribe (sekundy). Zapobiega wieszającym się requestom.
FAL_AI_CALL_TIMEOUT = 180


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


def evaluate_white_background(img: PIL.Image.Image) -> dict:
    """Ocena bieli tła na obramowaniu obrazu (dla kompozytów)."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    if w < 10 or h < 10:
        return {
            "border_white_ratio": 0.0,
            "border_mean_rgb": [0.0, 0.0, 0.0],
            "color_cast_max": 255.0,
            "white_bg_score": 0.0,
            "pass": False,
        }

    bw = max(2, int(w * 0.06))
    bh = max(2, int(h * 0.06))
    strips = [
        rgb.crop((0, 0, w, bh)),
        rgb.crop((0, h - bh, w, h)),
        rgb.crop((0, 0, bw, h)),
        rgb.crop((w - bw, 0, w, h)),
    ]

    total = 0
    white_count = 0
    sum_r = 0.0
    sum_g = 0.0
    sum_b = 0.0
    for strip in strips:
        for r, g, b in strip.getdata():
            total += 1
            sum_r += r
            sum_g += g
            sum_b += b
            if min(r, g, b) >= 249 and (max(r, g, b) - min(r, g, b)) <= 6:
                white_count += 1

    if total == 0:
        return {
            "border_white_ratio": 0.0,
            "border_mean_rgb": [0.0, 0.0, 0.0],
            "color_cast_max": 255.0,
            "white_bg_score": 0.0,
            "pass": False,
        }

    mean_r = sum_r / total
    mean_g = sum_g / total
    mean_b = sum_b / total
    border_white_ratio = white_count / total
    color_cast_max = max(abs(mean_r - mean_g), abs(mean_r - mean_b), abs(mean_g - mean_b))
    white_bg_score = max(
        0.0, min(1.0, 0.8 * border_white_ratio + 0.2 * (1.0 - color_cast_max / 10.0))
    )
    passed = (
        border_white_ratio >= 0.985
        and min(mean_r, mean_g, mean_b) >= 249
        and color_cast_max <= 3
    )
    return {
        "border_white_ratio": round(border_white_ratio, 4),
        "border_mean_rgb": [round(mean_r, 2), round(mean_g, 2), round(mean_b, 2)],
        "color_cast_max": round(color_cast_max, 2),
        "white_bg_score": round(white_bg_score, 4),
        "pass": passed,
    }


def enforce_pure_white_background(img: PIL.Image.Image) -> PIL.Image.Image:
    """Whitening obszarów tła połączonych z krawędzią (bez ruszania środka produktu)."""
    rgb = img.convert("RGB")
    px = rgb.load()
    w, h = rgb.size
    visited = bytearray(w * h)
    q: deque[tuple[int, int]] = deque()

    def idx(x: int, y: int) -> int:
        return y * w + x

    def qualifies(x: int, y: int) -> bool:
        r, g, b = px[x, y]
        return min(r, g, b) >= 228 and (max(r, g, b) - min(r, g, b)) <= 26

    def enqueue(x: int, y: int) -> None:
        i = idx(x, y)
        if visited[i]:
            return
        visited[i] = 1
        if qualifies(x, y):
            q.append((x, y))

    for x in range(w):
        enqueue(x, 0)
        enqueue(x, h - 1)
    for y in range(1, h - 1):
        enqueue(0, y)
        enqueue(w - 1, y)

    while q:
        x, y = q.popleft()
        px[x, y] = (255, 255, 255)
        if x > 0:
            enqueue(x - 1, y)
        if x < w - 1:
            enqueue(x + 1, y)
        if y > 0:
            enqueue(x, y - 1)
        if y < h - 1:
            enqueue(x, y + 1)

    return rgb


def _extract_image_from_gemini_response(response) -> PIL.Image.Image | None:
    """Wyciąga PIL Image z odpowiedzi Gemini."""
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
    """Bazowy interfejs dla wszystkich generatorów obrazów."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        reference_images: list[PIL.Image.Image] | None = None,
        target_size: tuple[int, int] = LIFESTYLE_SIZE,
        seed: int | None = None,
    ) -> PIL.Image.Image | None:
        ...

    @abstractmethod
    def cost_per_image(self) -> float:
        ...

    @abstractmethod
    def name(self) -> str:
        ...

    async def health_check(self) -> bool:
        """Sprawdza dostępność providera. Default: True."""
        return True

    def max_reference_images(self) -> int:
        return 0

    async def generate_with_retry(
        self,
        prompt: str,
        reference_images: list[PIL.Image.Image] | None = None,
        target_size: tuple[int, int] = LIFESTYLE_SIZE,
        max_retries: int = 3,
        seed: int | None = None,
    ) -> PIL.Image.Image | None:
        """Generate z exponential backoff. Retry WEWNĄTRZ generatora."""
        for attempt in range(1, max_retries + 1):
            try:
                result = await self.generate(prompt, reference_images, target_size, seed=seed)
                if result is not None:
                    return normalize_output(result, target_size)
                if attempt < max_retries:
                    logger.warning(
                        f"{self.name()} zwrócił None, retry {attempt}/{max_retries}"
                    )
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                err = str(e)
                retryable = any(
                    code in err for code in ["429", "500", "503", "RESOURCE_EXHAUSTED", "TimeoutError"]
                ) or isinstance(e, asyncio.TimeoutError)
                if attempt < max_retries and retryable:
                    wait = 5 * (2 ** attempt) + random.uniform(0, 2)
                    logger.warning(
                        f"{self.name()} error retry {attempt}/{max_retries}: "
                        f"{err[:120]}, wait {wait:.1f}s"
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
    Do 10 zdjęć referencyjnych, Thinking mode, native API."""

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
        seed: int | None = None,
    ) -> PIL.Image.Image | None:
        from google.genai import types

        client = self._get_client()
        contents: list = [prompt]
        if reference_images:
            contents.extend(reference_images[:10])

        config_kwargs = {
            "response_modalities": ["IMAGE", "TEXT"],
        }
        if seed is not None:
            config_kwargs["seed"] = int(seed)
        if self._thinking_level:
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level=self._thinking_level
            )

        gen_config = types.GenerateContentConfig(**config_kwargs)

        loop = asyncio.get_running_loop()
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
    """Gemini 3 Pro Image - legacy generator, zachowany dla kompatybilności."""

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
        seed: int | None = None,
    ) -> PIL.Image.Image | None:
        from google.genai import types

        client = self._get_client()
        contents: list = [prompt]
        if reference_images:
            contents.extend(reference_images[:6])

        config_kwargs = {
            "response_modalities": ["IMAGE", "TEXT"],
            "image_config": types.ImageConfig(imageSize="2K"),
        }
        if seed is not None:
            config_kwargs["seed"] = int(seed)
        gen_config = types.GenerateContentConfig(**config_kwargs)

        loop = asyncio.get_running_loop()
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
    """Lokalne packshoty na białym tle z cieniem kontaktowym. Koszt $0."""

    async def generate(
        self,
        prompt: str,
        reference_images: list[PIL.Image.Image] | None = None,
        target_size: tuple[int, int] = PACKSHOT_SIZE,
        seed: int | None = None,
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

def _download_image_from_url_sync(url: str) -> PIL.Image.Image | None:
    """Pobiera obraz z URL (synchronicznie, do wywołania w executor)."""
    try:
        import requests
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        img = PIL.Image.open(io.BytesIO(resp.content))
        img.load()
        return img
    except Exception as e:
        logger.error(f"Błąd pobierania obrazu z {url[:80]}: {e}")
        return None


async def _download_image_from_url(url: str) -> PIL.Image.Image | None:
    """Pobiera obraz z URL bez blokowania event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _download_image_from_url_sync, url)


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
    Zachowuje geometrię produktu 1:1. $0.08 flat."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            os.environ["FAL_KEY"] = FAL_AI_API_KEY
            import fal_client
            self._client = fal_client
        return self._client

    async def generate(self, prompt, reference_images=None, target_size=LIFESTYLE_SIZE, seed: int | None = None):
        if not reference_images:
            logger.warning("KontextMax: brak reference image (produkt PNG)")
            return None

        client = self._get_client()
        product_uri = _pil_to_base64_uri(reference_images[0])

        loop = asyncio.get_running_loop()
        arguments = {
            "prompt": prompt,
            "image_url": product_uri,
            "image_size": {"width": target_size[0], "height": target_size[1]},
            "num_images": 1,
            "output_format": "jpeg",
        }
        if seed is not None:
            arguments["seed"] = int(seed)

        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: client.subscribe(
                    KONTEXT_MAX_MODEL,
                    arguments=arguments,
                ),
            ),
            timeout=FAL_AI_CALL_TIMEOUT,
        )
        url = result["images"][0]["url"]
        return await _download_image_from_url(url)

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

    async def generate(self, prompt, reference_images=None, target_size=COMPOSITE_SIZE, seed: int | None = None):
        client = self._get_client()

        arguments = {
            "prompt": prompt,
            "image_size": {"width": target_size[0], "height": target_size[1]},
            "num_images": 1,
            "output_format": "jpeg",
        }
        if seed is not None:
            arguments["seed"] = int(seed)

        if reference_images:
            image_urls = [_pil_to_base64_uri(img) for img in reference_images[:9]]
            arguments["image_urls"] = image_urls

        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: client.subscribe(
                    FLUX_2_PRO_EDIT_MODEL,
                    arguments=arguments,
                ),
            ),
            timeout=FAL_AI_CALL_TIMEOUT,
        )
        url = result["images"][0]["url"]
        return await _download_image_from_url(url)

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

    async def generate(self, prompt, reference_images=None, target_size=COMPOSITE_SIZE, seed: int | None = None):
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
        if seed is not None:
            arguments["seed"] = int(seed)

        if reference_images:
            image_urls = [_pil_to_base64_uri(img) for img in reference_images[:10]]
            arguments["image_urls"] = image_urls

        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: client.subscribe(
                    KLING_O3_MODEL,
                    arguments=arguments,
                ),
            ),
            timeout=FAL_AI_CALL_TIMEOUT,
        )
        url = result["images"][0]["url"]
        return await _download_image_from_url(url)

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

    async def generate(self, prompt, reference_images=None, target_size=LIFESTYLE_SIZE, seed: int | None = None):
        client = self._get_client()
        tw, th = target_size

        if tw > th:
            size = "1536x1024"
        elif th > tw:
            size = "1024x1536"
        else:
            size = "1024x1024"

        loop = asyncio.get_running_loop()

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
            return await _download_image_from_url(image_data.url)
        logger.warning(
            f"GPT Image 1.5: brak b64_json/url w odpowiedzi. "
            f"Atrybuty: {[a for a in dir(image_data) if not a.startswith('_')]}"
        )
        return None

    def cost_per_image(self): return COST_GPT_IMAGE_USD
    def name(self): return "GPT Image 1.5"
    def max_reference_images(self): return 16
    async def health_check(self): return bool(OPENAI_API_KEY)


# ---------------------------------------------------------------------------
# Flux 2 LoRA via FAL.AI
# ---------------------------------------------------------------------------

class Flux2LoRAGenerator(ImageGenerator):
    """Flux 2 LoRA - wytrenowane LoRA via FAL.AI. Max 3 LoRA jednocześnie.
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

    async def generate(self, prompt, reference_images=None, target_size=LIFESTYLE_SIZE, seed: int | None = None):
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
        if seed is not None:
            arguments["seed"] = int(seed)

        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: client.subscribe(
                    FLUX_2_LORA_MODEL,
                    arguments=arguments,
                ),
            ),
            timeout=FAL_AI_CALL_TIMEOUT,
        )
        url = result["images"][0]["url"]
        return await _download_image_from_url(url)

    def cost_per_image(self): return COST_FLUX_2_LORA_IMAGE_USD
    def name(self): return "Flux 2 LoRA"
    def max_reference_images(self): return 3
    async def health_check(self): return bool(FAL_AI_API_KEY and self._get_lora_url())


# ---------------------------------------------------------------------------
# Flux 2 LoRA Edit via FAL.AI (primary v5.1)
# ---------------------------------------------------------------------------

class Flux2LoRAEditGenerator(Flux2LoRAGenerator):
    """Flux 2 LoRA Edit - LoRA + edycja obrazów referencyjnych (max 3 refs)."""

    async def generate(self, prompt, reference_images=None, target_size=COMPOSITE_SIZE, seed: int | None = None):
        lora_url = self._get_lora_url()
        if not lora_url:
            logger.warning("Flux2LoRAEdit: brak LoRA URL (config + rejestr)")
            return None
        if not reference_images:
            logger.warning("Flux2LoRAEdit: brak reference images")
            return None

        client = self._get_client()
        image_urls = [_pil_to_base64_uri(img) for img in reference_images[:3]]
        arguments = {
            "prompt": prompt,
            "image_urls": image_urls,
            "image_size": {"width": target_size[0], "height": target_size[1]},
            "num_images": 1,
            "output_format": "jpeg",
            "num_inference_steps": 28,
            "guidance_scale": 2.5,
            "loras": [{"path": lora_url, "scale": LORA_WEIGHT}],
        }
        if seed is not None:
            arguments["seed"] = int(seed)

        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: client.subscribe(
                    FLUX_2_LORA_EDIT_MODEL,
                    arguments=arguments,
                ),
            ),
            timeout=FAL_AI_CALL_TIMEOUT,
        )
        url = result["images"][0]["url"]
        return await _download_image_from_url(url)

    def name(self): return "Flux 2 LoRA Edit"
    def max_reference_images(self): return 3


# ---------------------------------------------------------------------------
# Fallback chain
# ---------------------------------------------------------------------------

async def generate_with_fallback(
    chain: list[ImageGenerator],
    prompt: str,
    reference_images: list[PIL.Image.Image] | None = None,
    target_size: tuple[int, int] = LIFESTYLE_SIZE,
    seed: int | None = None,
    prompt_factory: Callable[[ImageGenerator], str] | None = None,
) -> tuple[PIL.Image.Image | None, str, float]:
    """Próbuje generatory z listy po kolei. Zwraca (image, model_name, cost)."""
    for gen in chain:
        healthy = await gen.health_check()
        if not healthy:
            logger.warning(f"Fallback skip {gen.name()}: health check failed")
            continue

        logger.info(f"Trying generator: {gen.name()}")
        current_prompt = prompt
        if prompt_factory is not None:
            try:
                built = prompt_factory(gen)
                if built:
                    current_prompt = built
            except Exception as e:
                logger.warning(f"prompt_factory failed for {gen.name()}: {e}")
        result = await gen.generate_with_retry(
            current_prompt, reference_images, target_size, max_retries=2, seed=seed
        )
        if result is not None:
            return result, gen.name(), gen.cost_per_image()

        logger.warning(f"Fallback: {gen.name()} failed, trying next")

    logger.error("All generators in chain failed")
    return None, "none", 0.0


def get_lifestyle_generators() -> list[ImageGenerator]:
    """Zwraca instancje generatorów lifestyle (aktualnie dostępnych)."""
    gens: list[ImageGenerator] = []
    if LORA_PRIMARY_ENABLED:
        if LORA_EDIT_ENABLED:
            gens.append(Flux2LoRAEditGenerator())
        else:
            gens.append(Flux2LoRAGenerator())
        gens.append(KontextMaxGenerator())
    else:
        gens.append(KontextMaxGenerator())
        gens.append(Flux2LoRAGenerator())
    gens.append(GeminiFlashImageGenerator(thinking_level="HIGH"))
    gens.append(GeminiProImageGenerator())
    return gens


def get_composite_generators() -> list[ImageGenerator]:
    """Zwraca instancje generatorów kompozytów (v5.1 LoRA-first)."""
    gens: list[ImageGenerator] = []
    if LORA_PRIMARY_ENABLED:
        if LORA_EDIT_ENABLED:
            gens.append(Flux2LoRAEditGenerator())
        else:
            gens.append(Flux2LoRAGenerator())
    gens.append(Flux2ProEditGenerator())
    gens.append(GeminiFlashImageGenerator(thinking_level="HIGH"))
    gens.append(GeminiProImageGenerator())
    gens.append(PillowPackshotGenerator())
    return gens


async def get_provider_status() -> dict:
    """Health check wszystkich providerów."""
    providers = {
        "gemini": {
            "configured": bool(GEMINI_API_KEY),
            "models": [GEMINI_FLASH_IMAGE_MODEL, GEMINI_PRO_IMAGE_MODEL],
        },
        "fal_ai": {
            "configured": bool(FAL_AI_API_KEY),
            "models": [KONTEXT_MAX_MODEL, FLUX_2_PRO_EDIT_MODEL, FLUX_2_LORA_MODEL, FLUX_2_LORA_EDIT_MODEL, KLING_O3_MODEL],
        },
        "openai": {
            "configured": bool(OPENAI_API_KEY),
            "models": [OPENAI_IMAGE_MODEL],
        },
    }

    for name, info in providers.items():
        info["status"] = "active" if info["configured"] else "missing_key"

    return providers
