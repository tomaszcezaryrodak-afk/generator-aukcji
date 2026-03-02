#!/usr/bin/env python3
"""Lekkie testy jednostkowe dla zmian v5.1 (bez wywołań zewnętrznych API)."""

import asyncio

import PIL.Image

import image_generators as ig
from api import _compute_job_seed


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_white_background_metrics() -> None:
    white = PIL.Image.new("RGB", (400, 400), (255, 255, 255))
    metrics = ig.evaluate_white_background(white)
    _assert(metrics["pass"], f"Pure white image should pass: {metrics}")

    gray_border = PIL.Image.new("RGB", (400, 400), (255, 255, 255))
    px = gray_border.load()
    for x in range(400):
        for y in range(20):
            px[x, y] = (235, 235, 235)
            px[x, 399 - y] = (235, 235, 235)
    for y in range(400):
        for x in range(20):
            px[x, y] = (235, 235, 235)
            px[399 - x, y] = (235, 235, 235)
    gray_metrics = ig.evaluate_white_background(gray_border)
    _assert(not gray_metrics["pass"], f"Gray border should fail white gate: {gray_metrics}")

    fixed = ig.enforce_pure_white_background(gray_border)
    fixed_metrics = ig.evaluate_white_background(fixed)
    _assert(fixed_metrics["pass"], f"Autofix should pass white gate: {fixed_metrics}")


def test_job_seed_determinism() -> None:
    dna = {"product_type": "zlew", "color": "czarny", "shape": "prostokątny", "visible_elements": ["zlew"]}
    s1 = _compute_job_seed("job-1", dna)
    s2 = _compute_job_seed("job-1", dna)
    s3 = _compute_job_seed("job-2", dna)
    _assert(s1 == s2, "Seed must be deterministic for same input")
    _assert(s1 != s3, "Seed should differ for different job ids")


async def test_flux2_lora_edit_payload_seed() -> None:
    class _FakeClient:
        def __init__(self):
            self.last_model = ""
            self.last_arguments = {}

        def subscribe(self, model, arguments):
            self.last_model = model
            self.last_arguments = arguments
            return {"images": [{"url": "https://example.com/fake.jpg"}]}

    fake_client = _FakeClient()
    gen = ig.Flux2LoRAEditGenerator()
    gen._client = fake_client
    gen._get_lora_url = lambda: "https://example.com/fake_lora.safetensors"  # type: ignore[method-assign]

    old_download = ig._download_image_from_url

    async def _fake_download(_url: str):
        return PIL.Image.new("RGB", (64, 64), (255, 255, 255))

    ig._download_image_from_url = _fake_download  # type: ignore[assignment]
    try:
        ref = PIL.Image.new("RGB", (64, 64), (250, 250, 250))
        out = await gen.generate(
            prompt="test prompt",
            reference_images=[ref],
            target_size=(512, 512),
            seed=1234,
        )
        _assert(out is not None, "Generator should return image with fake client")
        _assert(fake_client.last_model == ig.FLUX_2_LORA_EDIT_MODEL, "Wrong model id used")
        _assert(fake_client.last_arguments.get("seed") == 1234, "Seed missing in payload")
        _assert("loras" in fake_client.last_arguments, "LoRA payload missing")
        _assert("image_urls" in fake_client.last_arguments, "image_urls payload missing")
    finally:
        ig._download_image_from_url = old_download  # type: ignore[assignment]


def main() -> None:
    test_white_background_metrics()
    test_job_seed_determinism()
    asyncio.run(test_flux2_lora_edit_payload_seed())
    print("test_v5_unit.py: ALL TESTS PASSED")


if __name__ == "__main__":
    main()
