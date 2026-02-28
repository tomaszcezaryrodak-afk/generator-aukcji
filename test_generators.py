#!/usr/bin/env python3
"""
Test generatorow obrazow (nie-LoRA).
Sprawdza: API connectivity, generowanie, normalize_output, zapis.
Uzycie: .venv/bin/python3 test_generators.py [--model MODEL_NAME]
"""
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

fal_key = os.environ.get("FAL_AI_API_KEY", "")
if fal_key:
    os.environ["FAL_KEY"] = fal_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

import PIL.Image
from image_generators import (
    KontextMaxGenerator,
    GeminiFlashImageGenerator,
    GeminiProImageGenerator,
    GPTImage15Generator,
    Flux2ProEditGenerator,
    KlingO3Generator,
    PillowPackshotGenerator,
    normalize_output,
    get_lifestyle_generators,
    get_composite_generators,
    generate_with_fallback,
    get_provider_status,
)
from config import PACKSHOT_SIZE, LIFESTYLE_SIZE, COMPOSITE_SIZE

# --- Test data ---
TEST_IMAGE_PATH = "training/packshots/farmerski/9bc4663af75282567a003c2a5ebe9676de09a4912a7ad1039333bf3e3ef2474d.png"
OUTPUT_DIR = Path("test_output")

LIFESTYLE_PROMPT = (
    "REAL PHOTOGRAPH Canon EOS R5, 85mm f/1.4 lens. Natural daylight 5500K. "
    "Granite kitchen sink installed in oak wood countertop, overhead bird's eye view. "
    "Accessories: ceramic mug, fresh herbs, wooden cutting board, linen cloth. "
    "Matte stone surface with mineral speckles. Realistic contact shadow. "
    "NOT 3D render, NOT CGI. Subtle grain ISO 400."
)

COMPOSITE_PROMPT = (
    "Pure white studio background RGB(255,255,255). Professional product photograph "
    "Canon EOS R5, 50mm f/1.8, studio 3-point softbox lighting. "
    "Granite kitchen sink shown from top-down bird's eye view. "
    "Clean packshot with subtle natural contact shadow at base. "
    "PRESERVATION: exactly consistent product proportions, colors, textures. "
    "8K UHD quality."
)


def load_test_image() -> PIL.Image.Image:
    """Laduje testowy obraz produktu."""
    path = Path(TEST_IMAGE_PATH)
    if not path.exists():
        raise FileNotFoundError(f"Brak obrazu testowego: {path}")
    img = PIL.Image.open(path)
    img.load()
    logger.info(f"Zaladowano obraz testowy: {path} ({img.size}, {img.mode})")
    return img


async def test_health_checks():
    """Sprawdza health check wszystkich providerow."""
    logger.info("=" * 60)
    logger.info("HEALTH CHECK providerow")
    logger.info("=" * 60)

    status = await get_provider_status()
    for name, info in status.items():
        logger.info(f"  {name}: {info['status']} (modele: {', '.join(info['models'])})")

    generators = [
        KontextMaxGenerator(),
        GeminiFlashImageGenerator(),
        GPTImage15Generator(),
        Flux2ProEditGenerator(),
        KlingO3Generator(),
        PillowPackshotGenerator(),
    ]
    for gen in generators:
        healthy = await gen.health_check()
        logger.info(f"  {gen.name()}: {'OK' if healthy else 'FAIL'} (${gen.cost_per_image():.3f}/img)")

    return status


async def test_single_generator(
    gen_class,
    prompt: str,
    ref_images: list[PIL.Image.Image] | None,
    target_size: tuple[int, int],
    label: str,
) -> dict:
    """Testuje pojedynczy generator."""
    gen = gen_class() if isinstance(gen_class, type) else gen_class
    result = {
        "name": gen.name(),
        "label": label,
        "success": False,
        "time_sec": 0,
        "cost_usd": gen.cost_per_image(),
        "output_size": None,
        "output_path": None,
        "error": None,
    }

    logger.info(f"\n{'=' * 60}")
    logger.info(f"TEST: {gen.name()} ({label})")
    logger.info(f"  Prompt: {prompt[:80]}...")
    logger.info(f"  Refs: {len(ref_images) if ref_images else 0}")
    logger.info(f"  Target: {target_size}")

    healthy = await gen.health_check()
    if not healthy:
        result["error"] = "Health check failed"
        logger.warning(f"  SKIP: health check failed")
        return result

    t0 = time.time()
    try:
        img = await gen.generate_with_retry(
            prompt, ref_images, target_size, max_retries=2
        )
        elapsed = time.time() - t0
        result["time_sec"] = round(elapsed, 1)

        if img is not None:
            result["success"] = True
            result["output_size"] = img.size

            out_name = f"{gen.name().lower().replace(' ', '_')}_{label}.jpg"
            out_path = OUTPUT_DIR / out_name
            img.save(out_path, "JPEG", quality=92)
            result["output_path"] = str(out_path)

            logger.info(f"  OK: {img.size} w {elapsed:.1f}s -> {out_path}")
        else:
            result["error"] = "Generator zwrocil None"
            logger.warning(f"  FAIL: None w {elapsed:.1f}s")

    except Exception as e:
        elapsed = time.time() - t0
        result["time_sec"] = round(elapsed, 1)
        result["error"] = str(e)[:200]
        logger.error(f"  ERROR ({elapsed:.1f}s): {e}")

    return result


async def test_fallback_chain(
    chain_fn,
    prompt: str,
    ref_images: list[PIL.Image.Image] | None,
    target_size: tuple[int, int],
    label: str,
) -> dict:
    """Testuje pelny fallback chain."""
    logger.info(f"\n{'=' * 60}")
    logger.info(f"FALLBACK CHAIN: {label}")

    generators = chain_fn()
    chain_names = [g.name() for g in generators]
    logger.info(f"  Chain: {' -> '.join(chain_names)}")

    t0 = time.time()
    img, model_name, cost = await generate_with_fallback(
        generators, prompt, ref_images, target_size
    )
    elapsed = time.time() - t0

    result = {
        "label": label,
        "chain": chain_names,
        "winner": model_name,
        "success": img is not None,
        "time_sec": round(elapsed, 1),
        "cost_usd": cost,
    }

    if img is not None:
        out_name = f"chain_{label}_{model_name.lower().replace(' ', '_')}.jpg"
        out_path = OUTPUT_DIR / out_name
        img.save(out_path, "JPEG", quality=92)
        result["output_path"] = str(out_path)
        logger.info(f"  OK: {model_name} ({img.size}) w {elapsed:.1f}s -> {out_path}")
    else:
        logger.error(f"  FAIL: caly chain zawiodl w {elapsed:.1f}s")

    return result


async def main(model_filter: str | None = None):
    OUTPUT_DIR.mkdir(exist_ok=True)
    product_img = load_test_image()

    results = []

    # 1. Health checks
    await test_health_checks()

    # 2. Testy pojedynczych generatorow
    tests = [
        # (class, prompt, refs, size, label)
        (KontextMaxGenerator, LIFESTYLE_PROMPT, [product_img], LIFESTYLE_SIZE, "lifestyle"),
        (GeminiFlashImageGenerator, COMPOSITE_PROMPT, [product_img], COMPOSITE_SIZE, "composite"),
        (GeminiFlashImageGenerator, LIFESTYLE_PROMPT, [product_img], LIFESTYLE_SIZE, "lifestyle"),
        (GPTImage15Generator, LIFESTYLE_PROMPT, [product_img], LIFESTYLE_SIZE, "lifestyle"),
        (Flux2ProEditGenerator, COMPOSITE_PROMPT, [product_img], COMPOSITE_SIZE, "composite"),
        (KlingO3Generator, COMPOSITE_PROMPT, [product_img], COMPOSITE_SIZE, "composite"),
        (PillowPackshotGenerator, "packshot", [product_img], PACKSHOT_SIZE, "packshot"),
    ]

    if model_filter:
        tests = [t for t in tests if model_filter.lower() in t[0].__name__.lower()]

    for gen_class, prompt, refs, size, label in tests:
        r = await test_single_generator(gen_class, prompt, refs, size, label)
        results.append(r)

    # 3. Fallback chains (tylko jesli brak filtra)
    if not model_filter:
        r = await test_fallback_chain(
            get_lifestyle_generators, LIFESTYLE_PROMPT, [product_img], LIFESTYLE_SIZE, "lifestyle"
        )
        results.append(r)

        r = await test_fallback_chain(
            get_composite_generators, COMPOSITE_PROMPT, [product_img], COMPOSITE_SIZE, "composite"
        )
        results.append(r)

    # 4. Podsumowanie
    logger.info(f"\n{'=' * 60}")
    logger.info("PODSUMOWANIE TESTOW")
    logger.info(f"{'=' * 60}")

    total_cost = 0
    passed = 0
    failed = 0

    for r in results:
        name = r.get("name", r.get("label", "?"))
        label = r.get("label", "")
        status = "PASS" if r["success"] else "FAIL"
        cost = r.get("cost_usd", 0)
        t = r.get("time_sec", 0)
        err = r.get("error", "")

        if r["success"]:
            passed += 1
            total_cost += cost
        else:
            failed += 1

        line = f"  {status} {name} ({label}): {t}s, ${cost:.3f}"
        if err:
            line += f" [{err[:60]}]"
        logger.info(line)

    logger.info(f"\n  Wynik: {passed}/{passed + failed} passed")
    logger.info(f"  Koszt testow: ${total_cost:.3f}")
    logger.info(f"  Outputy: {OUTPUT_DIR}/")

    return results


if __name__ == "__main__":
    model_filter = None
    if len(sys.argv) > 1 and sys.argv[1] == "--model":
        model_filter = sys.argv[2] if len(sys.argv) > 2 else None

    asyncio.run(main(model_filter))
