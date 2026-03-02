#!/usr/bin/env python3
"""
Standalone pipeline: packshot -> lifestyle (4 warianty)

Użycie:
    python pipeline_lifestyle.py --input packshot.jpg --output ./output/
    python pipeline_lifestyle.py --input packshot.jpg --output ./output/ --scenes 2  # tylko 2 sceny
    python pipeline_lifestyle.py --batch ./packshoty/ --output ./output/  # batch

Wymaga:
    pip install google-genai Pillow rembg[cpu] python-dotenv

Env vars:
    GEMINI_API_KEY (wymagany)
    GEMINI_MODEL (opcjonalny, default: gemini-3-pro-image-preview)
    RATE_LIMIT_SEC (opcjonalny, default: 2)
"""

import asyncio
import io
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import PIL.Image
from PIL import ImageFilter, ImageStat

try:
    from rembg import remove as rembg_remove, new_session as rembg_new_session

    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False
    print("[WARN] rembg niedostępne. pip install rembg[cpu]")

from google import genai
from google.genai import types

# --- Konfiguracja ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-pro-image-preview")
RATE_LIMIT_SEC = float(os.environ.get("RATE_LIMIT_SEC", "2"))
RETRY_THRESHOLD = 7
MAX_RETRIES = 2

COST_PER_IMAGE_USD = 0.134
COST_PER_TEXT_USD = 0.02
USD_TO_PLN = 3.57


# ---------------------------------------------------------------------------
# Sceny lifestyle
# ---------------------------------------------------------------------------

LIFESTYLE_SCENES = [
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
]


# ---------------------------------------------------------------------------
# Krok 1: Background removal
# ---------------------------------------------------------------------------

_rembg_session = None


def remove_background(pil_image: PIL.Image.Image) -> PIL.Image.Image:
    """Usuwa tło ze zdjęcia. Zwraca PIL Image RGBA."""
    global _rembg_session
    if not REMBG_AVAILABLE:
        print("  [WARN] rembg niedostępne, zwracam oryginał z kanałem alpha")
        return pil_image.convert("RGBA")
    if _rembg_session is None:
        print("  Ładowanie modelu birefnet-general (pierwszy raz, ~10s)...")
        _rembg_session = rembg_new_session("birefnet-general")
    return rembg_remove(pil_image, session=_rembg_session)


# ---------------------------------------------------------------------------
# Krok 2: Product DNA
# ---------------------------------------------------------------------------


def get_product_dna_prompt() -> str:
    return """You are a product photography analyst for a granite kitchen sink e-commerce store.

Analyze the product image(s) provided. Describe EXACTLY what you see. Do NOT guess, infer, or add elements that are not visible.

Return a JSON object with the following fields (use Polish for all string values):

{
  "product_type": "type of product, e.g. zlew granitowy nablatowy, bateria kuchenna, zestaw zlew + bateria",
  "shape": "overall shape, e.g. kwadratowy, prostokatny z ociekaczem, okragly",
  "color": "dominant color, e.g. bialy, czarny nakrapiany, szary",
  "mounting_type": "nablatowy, wpuszczany, podwieszany, or null if not determinable",
  "has_drainboard": true,
  "has_faucet_hole": true,
  "bowl_count": 1,
  "bowl_shape": "kwadratowa, prostokatna, or okragla",
  "drain_position": "srodek, prawy, or lewy",
  "drain_type": "kwadratowy, okragly, or automatyczny",
  "visible_elements": ["list of ALL elements visible in the image"],
  "NOT_present": ["list of elements that are NOT in the image"],
  "material_texture": "texture description",
  "approximate_dimensions": "estimated size",
  "distinctive_features": ["unique traits"]
}

RULES:
- Respond with ONLY the JSON object. No extra text, no markdown code blocks, no explanation.
- If a field cannot be determined from the image, use null.
- Be precise about what IS and what IS NOT in the image.
- visible_elements: list EVERY distinct physical element you can see.
- NOT_present: list common kitchen sink accessories that are ABSENT (bateria, dozownik, ociekacz, syfon, deska do krojenia, koszyk, etc.)."""


async def analyze_product_dna(client, pil_images: list) -> str:
    """Analizuje produkt. Zwraca JSON string."""
    prompt = get_product_dna_prompt()
    response = await asyncio.to_thread(
        lambda: client.models.generate_content(
            model=MODEL,
            contents=[prompt] + pil_images[:2],
            config=types.GenerateContentConfig(response_modalities=["TEXT"]),
        )
    )
    if response.candidates and response.parts:
        for part in response.parts:
            if part.text:
                text = part.text.strip()
                if text.startswith("```"):
                    lines = text.split("\n")
                    text = (
                        "\n".join(lines[1:-1])
                        if lines[-1].strip() == "```"
                        else "\n".join(lines[1:])
                    )
                return text
    return "{}"


# ---------------------------------------------------------------------------
# Krok 3: Packshoty (Pillow)
# ---------------------------------------------------------------------------


def create_studio_packshots(
    transparent_img: PIL.Image.Image,
) -> list[PIL.Image.Image]:
    """2 packshoty: produkt na białym tle z cieniem."""
    results = []
    canvas_w, canvas_h = 1200, 900

    # Packshot 1: centrowany (80% canvas) z cieniem
    canvas = PIL.Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))
    product = transparent_img.copy()
    max_w, max_h = int(canvas_w * 0.8), int(canvas_h * 0.8)
    ratio = min(max_w / product.width, max_h / product.height)
    if ratio < 1:
        product = product.resize(
            (int(product.width * ratio), int(product.height * ratio)),
            PIL.Image.LANCZOS,
        )
    x = (canvas_w - product.width) // 2
    y = (canvas_h - product.height) // 2

    shadow = PIL.Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow.paste(
        PIL.Image.new("RGBA", product.size, (0, 0, 0, 40)),
        (x + 8, y + 8),
        mask=product.split()[3],
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    canvas = PIL.Image.alpha_composite(canvas, shadow)
    canvas.paste(product, (x, y), mask=product)
    results.append(canvas.convert("RGB"))

    # Packshot 2: zmniejszony (65%) z większym marginesem
    canvas2 = PIL.Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))
    product2 = transparent_img.copy()
    ratio2 = min((canvas_w * 0.65) / product2.width, (canvas_h * 0.65) / product2.height)
    if ratio2 < 1:
        product2 = product2.resize(
            (int(product2.width * ratio2), int(product2.height * ratio2)),
            PIL.Image.LANCZOS,
        )
    x2 = (canvas_w - product2.width) // 2
    y2 = (canvas_h - product2.height) // 2

    shadow2 = PIL.Image.new("RGBA", canvas2.size, (0, 0, 0, 0))
    shadow2.paste(
        PIL.Image.new("RGBA", product2.size, (0, 0, 0, 30)),
        (x2 + 6, y2 + 6),
        mask=product2.split()[3],
    )
    shadow2 = shadow2.filter(ImageFilter.GaussianBlur(8))
    canvas2 = PIL.Image.alpha_composite(canvas2, shadow2)
    canvas2.paste(product2, (x2, y2), mask=product2)
    results.append(canvas2.convert("RGB"))

    return results


# ---------------------------------------------------------------------------
# Krok 4: Lifestyle (Gemini IMAGE)
# ---------------------------------------------------------------------------


def build_lifestyle_prompt(
    scene: dict, product_dna_json: str, corrections: str = ""
) -> str:
    """Prompt lifestyle z Product DNA."""
    no_text = "Do NOT add any text, labels, watermarks, or annotations to the image."
    quality = (
        "Crystal sharp focus, professional color grading, realistic material textures. "
        "Aspect ratio: 4:3 landscape (1200x900px)."
    )
    material = (
        "MATERIAL ACCURACY: granite = matte stone texture with visible mineral speckles, "
        "NOT plastic, NOT ceramic gloss. Metal parts = realistic metallic reflections "
        "matching specified finish."
    )
    negative = (
        "NEVER: text overlays, watermarks, plastic sheen on granite, blurry edges, "
        "floating objects, AI artifacts, distorted proportions, extra faucets or sinks."
    )

    try:
        dna = json.loads(product_dna_json)
    except (json.JSONDecodeError, TypeError):
        dna = {}

    visible = dna.get("visible_elements", [])
    not_present = dna.get("NOT_present", [])
    visible_str = (
        ", ".join(visible) if visible else "all elements from the reference image"
    )
    not_present_str = ", ".join(not_present) if not_present else "nothing extra"

    corrections_block = ""
    if corrections:
        corrections_block = (
            f"\n\nPREVIOUS ATTEMPT FAILED CHECK. Issues found:\n{corrections}\n"
            f"Fix these specific issues in this generation attempt."
        )

    return f"""You are generating a lifestyle kitchen photograph for an e-commerce product listing.

The transparent PNG of the real product is provided as input. You MUST use it as the exact reference.

=== PRODUCT DNA (from analysis of the original product) ===
{product_dna_json}

=== FIDELITY RULES (CRITICAL) ===
The product shape, color, mounting type, drain position, bowl count, and bowl shape MUST match EXACTLY what is described in the Product DNA above.
MUST include EXACTLY these elements: {visible_str}
Do NOT add: {not_present_str}
Do NOT invent, add, remove, or alter ANY part of the product. The generated product must be structurally identical to the input image.

=== SCENE ===
Scene: {scene.get('name', 'kitchen lifestyle')}
Countertop: {scene.get('countertop', 'wooden')}
Perspective: {scene.get('perspective', 'top-down overhead view')}
Props/details: {scene.get('details', 'minimal kitchen accessories')}

=== STYLE ===
Photojournalistic editorial kitchen photography. Realistic imperfections, lived-in kitchen, natural daylight, real photograph not a 3D render. Warm neutral color temperature.

{material}
{quality}
{negative}
{no_text}{corrections_block}"""


def generate_image(
    client, prompt: str, reference_images: list, task_name: str
) -> PIL.Image.Image | None:
    """Generuje obraz przez Gemini. Zwraca PIL Image lub None."""
    gen_config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(imageSize="2K"),
    )
    contents = [prompt] + reference_images

    for attempt in range(1, 4):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=gen_config,
            )
            if not response.parts or not response.candidates:
                return None
            for part in response.parts:
                if part.inline_data is not None and part.inline_data.data:
                    img = PIL.Image.open(io.BytesIO(part.inline_data.data))
                    img.load()
                    print(f"  [OK] {task_name}")
                    return img
            return None
        except Exception as e:
            error_str = str(e)
            if attempt < 3 and any(
                code in error_str
                for code in ["429", "500", "503", "RESOURCE_EXHAUSTED"]
            ):
                wait = 10 * attempt
                print(f"  [RETRY {attempt}] {task_name}: {error_str[:80]} (czekam {wait}s)")
                time.sleep(wait)
            else:
                raise
    return None


# ---------------------------------------------------------------------------
# Krok 5: Self-check
# ---------------------------------------------------------------------------


def get_selfcheck_prompt(product_dna_json: str) -> str:
    return f"""You are a quality control inspector for e-commerce product photography.

You will receive TWO images:
1. FIRST image: the ORIGINAL product photo (reference, ground truth)
2. SECOND image: the AI-GENERATED lifestyle photo that should contain the same product

Compare the product in the generated image against the original. Score each dimension 1-10:

- shape_score: Does the product shape match? (bowl shape, drainboard, proportions, mounting)
- color_score: Does the color match? (base color, speckle pattern, finish type)
- detail_score: Are all visible elements correct? (drain, faucet hole, accessories)
- overall_score: Weighted average (shape 40%, color 30%, detail 30%)

=== PRODUCT DNA (expected) ===
{product_dna_json}

Return ONLY JSON (no code blocks, no extra text):
{{
  "shape_score": 8,
  "color_score": 7,
  "detail_score": 8,
  "overall_score": 8,
  "differences": ["roznice po polsku"],
  "corrections_needed": "English instructions for retry"
}}

Be strict. 7 = noticeable differences. 5 = significant errors. Below 5 = wrong product."""


async def run_selfcheck(
    client,
    original: PIL.Image.Image,
    generated: PIL.Image.Image,
    product_dna_json: str,
) -> tuple[int, list, str]:
    """Porównuje wygenerowane z oryginałem. Zwraca (score, differences, corrections)."""
    prompt = get_selfcheck_prompt(product_dna_json)
    response = await asyncio.to_thread(
        lambda: client.models.generate_content(
            model=MODEL,
            contents=[prompt, original, generated],
            config=types.GenerateContentConfig(response_modalities=["TEXT"]),
        )
    )
    if response.candidates and response.parts:
        for part in response.parts:
            if part.text:
                text = part.text.strip()
                if text.startswith("```"):
                    lines = text.split("\n")
                    text = (
                        "\n".join(lines[1:-1])
                        if lines[-1].strip() == "```"
                        else "\n".join(lines[1:])
                    )
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


# ---------------------------------------------------------------------------
# Dodatkowe metryki jakości (lokalne, bez API)
# ---------------------------------------------------------------------------


def quality_metrics(generated: PIL.Image.Image) -> dict:
    """Lokalne metryki jakości (rozdzielczość, jasność, kontrast)."""
    w, h = generated.size
    stat = ImageStat.Stat(generated)
    mean_brightness = stat.mean[0]
    std_dev = stat.stddev[0]
    r, g, b = stat.mean[:3]
    color_variance = max(r, g, b) - min(r, g, b)

    return {
        "resolution": f"{w}x{h}",
        "resolution_ok": w >= 1200 and h >= 900,
        "brightness_mean": round(mean_brightness, 1),
        "brightness_ok": 80 < mean_brightness < 220,
        "contrast_stddev": round(std_dev, 1),
        "contrast_ok": std_dev > 30,
        "color_variance": round(color_variance, 1),
        "color_balance_ok": color_variance > 10,
    }


# ---------------------------------------------------------------------------
# Pipeline główny
# ---------------------------------------------------------------------------


async def run_pipeline(
    input_path: str,
    output_dir: str,
    max_scenes: int = 4,
) -> dict:
    """Pełny pipeline: packshot -> 2 packshoty + N lifestyle."""
    if not GEMINI_API_KEY:
        print("BŁĄD: Brak GEMINI_API_KEY w zmiennych środowiskowych.")
        sys.exit(1)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    scenes = LIFESTYLE_SCENES[:max_scenes]

    stats = {
        "input": input_path,
        "output_dir": output_dir,
        "image_api_calls": 0,
        "text_api_calls": 0,
        "retries": 0,
        "total_time_s": 0,
        "cost_usd": 0.0,
        "cost_pln": 0.0,
        "results": {},
        "scores": {},
        "quality_metrics": {},
    }

    t0 = time.time()

    # Ładuj obraz
    original = PIL.Image.open(input_path)
    original.load()
    print(f"\n[1/6] Załadowano: {input_path} ({original.size[0]}x{original.size[1]})")

    # Krok 1: Background removal
    print("\n[2/6] Usuwanie tła (rembg)...")
    t_bg = time.time()
    transparent = remove_background(original)
    transparent_path = output_path / "transparent.png"
    transparent.save(str(transparent_path))
    print(
        f"  [OK] transparent.png ({transparent.size[0]}x{transparent.size[1]}) "
        f"w {time.time() - t_bg:.1f}s"
    )

    # Krok 2: Product DNA
    print("\n[3/6] Analiza produktu (Product DNA)...")
    client = genai.Client(api_key=GEMINI_API_KEY)
    product_dna = await analyze_product_dna(client, [original])
    stats["text_api_calls"] += 1

    dna_path = output_path / "product_dna.json"
    dna_path.write_text(product_dna, encoding="utf-8")

    try:
        dna_parsed = json.loads(product_dna)
        print(f"  Typ: {dna_parsed.get('product_type', '?')}")
        print(f"  Kolor: {dna_parsed.get('color', '?')}")
        print(f"  Kształt: {dna_parsed.get('shape', '?')}")
        print(f"  Montaż: {dna_parsed.get('mounting_type', '?')}")
        visible = dna_parsed.get("visible_elements", [])
        not_present = dna_parsed.get("NOT_present", [])
        if visible:
            print(f"  Widoczne: {', '.join(visible)}")
        if not_present:
            print(f"  Brak: {', '.join(not_present)}")
    except json.JSONDecodeError:
        print("  [WARN] Product DNA nie jest poprawnym JSON")

    await asyncio.sleep(RATE_LIMIT_SEC)

    # Krok 3: Packshoty
    print("\n[4/6] Tworzenie packshotów (Pillow, 0 API calls)...")
    packshots = create_studio_packshots(transparent)
    for i, pack in enumerate(packshots):
        pack_key = f"packshot_{i + 1}"
        pack_path = output_path / f"{pack_key}.png"
        pack.save(str(pack_path))
        stats["results"][pack_key] = str(pack_path)
        print(f"  [OK] {pack_key}.png")

    # Krok 4+5+6: Lifestyle + Self-check + Retry
    print(f"\n[5/6] Generowanie lifestyle ({len(scenes)} scen)...")
    reference_images = [transparent]

    for idx, scene in enumerate(scenes):
        scene_name = scene["name"]
        print(f"\n  --- Scena {idx + 1}/{len(scenes)}: {scene_name} ---")

        prompt = build_lifestyle_prompt(scene, product_dna)
        best_score = 0
        best_img = None
        best_differences = []

        for attempt in range(1 + MAX_RETRIES):
            gen_img = await asyncio.to_thread(
                generate_image,
                client,
                prompt,
                reference_images,
                f"{scene_name} (próba {attempt + 1})",
            )
            stats["image_api_calls"] += 1

            if not gen_img:
                print(f"  [FAIL] Brak obrazu w odpowiedzi Gemini")
                break

            await asyncio.sleep(RATE_LIMIT_SEC)

            # Self-check
            score, differences, corrections = await run_selfcheck(
                client, original, gen_img, product_dna
            )
            stats["text_api_calls"] += 1

            print(f"  Self-check: score={score}/10")
            for diff in differences[:3]:
                print(f"    - {diff}")

            if score >= best_score:
                best_score = score
                best_img = gen_img
                best_differences = differences

            if score >= RETRY_THRESHOLD:
                break

            if attempt < MAX_RETRIES:
                stats["retries"] += 1
                print(
                    f"  [RETRY] Score {score} < {RETRY_THRESHOLD}, "
                    f"regeneracja z korektami (próba {attempt + 2})..."
                )
                prompt = build_lifestyle_prompt(
                    scene, product_dna, corrections=corrections
                )
                await asyncio.sleep(RATE_LIMIT_SEC)

        # Zapisz najlepszy wynik
        if best_img:
            safe_name = (
                scene_name.replace(" · ", "_")
                .replace(" ", "_")
                .replace("·", "")
                .lower()
            )
            key = f"lifestyle_{idx + 1}_{safe_name}"
            img_path = output_path / f"{key}.png"
            best_img.save(str(img_path))
            stats["results"][key] = str(img_path)
            stats["scores"][scene_name] = best_score

            # Lokalne metryki
            qm = quality_metrics(best_img)
            stats["quality_metrics"][scene_name] = qm

            status = "PASS" if best_score >= 7 else "WARN"
            print(f"  [{status}] {key}.png (score: {best_score}/10)")
        else:
            print(f"  [SKIP] {scene_name}: nie udało się wygenerować")

        await asyncio.sleep(RATE_LIMIT_SEC)

    # Podsumowanie
    t1 = time.time()
    stats["total_time_s"] = round(t1 - t0, 1)
    stats["cost_usd"] = round(
        stats["image_api_calls"] * COST_PER_IMAGE_USD
        + stats["text_api_calls"] * COST_PER_TEXT_USD,
        3,
    )
    stats["cost_pln"] = round(stats["cost_usd"] * USD_TO_PLN, 2)

    print(f"\n{'=' * 50}")
    print(f"[6/6] PODSUMOWANIE")
    print(f"{'=' * 50}")
    print(f"  Czas: {stats['total_time_s']}s")
    print(f"  API calls (image): {stats['image_api_calls']}")
    print(f"  API calls (text): {stats['text_api_calls']}")
    print(f"  Retry: {stats['retries']}")
    print(f"  Koszt: ${stats['cost_usd']} (~{stats['cost_pln']} PLN)")
    print(f"  Zdjęcia wygenerowane: {len(stats['results'])}")

    if stats["scores"]:
        avg_score = sum(stats["scores"].values()) / len(stats["scores"])
        print(f"  Średni score: {avg_score:.1f}/10")

        low_scores = {k: v for k, v in stats["scores"].items() if v < 7}
        if low_scores:
            print(f"  [WARN] Niskie scores: {low_scores}")

    # Zapisz raport
    report_path = output_path / "pipeline_report.json"
    report_path.write_text(
        json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n  Raport: {report_path}")

    return stats


# ---------------------------------------------------------------------------
# Batch pipeline
# ---------------------------------------------------------------------------


async def batch_pipeline(input_dir: str, output_base: str, max_scenes: int = 4):
    """Przetwarza wszystkie packshoty z katalogu."""
    input_path = Path(input_dir)
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    files = sorted(
        f for f in input_path.iterdir() if f.suffix.lower() in extensions
    )

    if not files:
        print(f"BŁĄD: Brak zdjęć w {input_dir}")
        return

    print(f"Znaleziono {len(files)} packshotów w {input_dir}")
    all_stats = []

    for i, f in enumerate(files, 1):
        product_name = f.stem
        output_dir = f"{output_base}/{product_name}"
        print(f"\n{'#' * 60}")
        print(f"# PRODUKT {i}/{len(files)}: {product_name}")
        print(f"{'#' * 60}")

        try:
            stats = await run_pipeline(str(f), output_dir, max_scenes=max_scenes)
            all_stats.append(stats)
        except Exception as e:
            print(f"  [ERROR] {product_name}: {e}")
            all_stats.append({"input": str(f), "error": str(e)})

        if i < len(files):
            print(f"\n  Pauza 5s przed następnym produktem...")
            await asyncio.sleep(5)

    # Podsumowanie batch
    print(f"\n{'#' * 60}")
    print(f"# PODSUMOWANIE BATCH")
    print(f"{'#' * 60}")
    total_cost = sum(s.get("cost_pln", 0) for s in all_stats)
    total_time = sum(s.get("total_time_s", 0) for s in all_stats)
    total_images = sum(len(s.get("results", {})) for s in all_stats)
    errors = sum(1 for s in all_stats if "error" in s)

    print(f"  Produkty: {len(files)} ({errors} błędów)")
    print(f"  Zdjęcia: {total_images}")
    print(f"  Czas: {total_time:.0f}s ({total_time / 60:.1f} min)")
    print(f"  Koszt: {total_cost:.2f} PLN")

    # Zapisz batch report
    batch_report = Path(output_base) / "batch_report.json"
    batch_report.write_text(
        json.dumps(all_stats, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  Raport: {batch_report}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Pipeline: packshot -> lifestyle (zlewy granitowe)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", help="Ścieżka do pojedynczego packshotu (JPEG/PNG)")
    group.add_argument("--batch", help="Katalog z packshotami (batch processing)")
    parser.add_argument("--output", default="./output", help="Katalog wyjściowy")
    parser.add_argument(
        "--scenes", type=int, default=4, choices=[1, 2, 3, 4],
        help="Liczba scen lifestyle (default: 4)",
    )
    args = parser.parse_args()

    if args.input:
        if not Path(args.input).exists():
            print(f"BŁĄD: Plik nie istnieje: {args.input}")
            sys.exit(1)
        asyncio.run(run_pipeline(args.input, args.output, max_scenes=args.scenes))
    else:
        if not Path(args.batch).is_dir():
            print(f"BŁĄD: Katalog nie istnieje: {args.batch}")
            sys.exit(1)
        asyncio.run(batch_pipeline(args.batch, args.output, max_scenes=args.scenes))
