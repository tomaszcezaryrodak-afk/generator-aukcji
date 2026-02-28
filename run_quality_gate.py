#!/usr/bin/env python3
"""
Quality gate: generuje 5 par obrazow (z LoRA vs bez LoRA).
Uruchom PO zakonczeniu treningu.
Uzycie: .venv/bin/python3 run_quality_gate.py
"""
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

fal_key = os.environ.get("FAL_AI_API_KEY", "")
if not fal_key:
    print("BLAD: Brak FAL_AI_API_KEY w .env")
    sys.exit(1)
os.environ["FAL_KEY"] = fal_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

from lora_training import LoRATrainer, LoRAConfig


async def main():
    trainer = LoRATrainer()

    # Pobierz aktywny URL z rejestru
    lora_url = trainer.get_active_lora_url()
    if not lora_url:
        # Fallback: czytaj z latest_lora_url.txt
        url_file = trainer._versions_dir / "latest_lora_url.txt"
        if url_file.exists():
            lora_url = url_file.read_text().strip()

    if not lora_url:
        print("BLAD: Brak aktywnego LoRA URL w rejestrze ani latest_lora_url.txt")
        sys.exit(1)

    logger.info(f"LoRA URL: {lora_url[:80]}...")
    logger.info("=== QUALITY GATE: 5 par (LoRA vs base) ===")

    validation = await trainer.validate(lora_url)

    logger.info("=== WYNIKI ===")
    logger.info(f"Testoow: {validation['test_count']}")
    logger.info(f"Obrazy LoRA: {validation['test_images_lora']}")
    logger.info(f"Obrazy base: {validation['test_images_base']}")
    logger.info(f"Katalog: training/lora_versions/test_results/")

    # Podsumowanie kosztow
    # 10 obrazow (5 LoRA + 5 base) x ~$0.063 = ~$0.63
    est_cost = 10 * 0.063
    logger.info(f"Szacowany koszt quality gate: ~${est_cost:.2f}")

    return validation


if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\nGOTOWE. Sprawdz obrazy w training/lora_versions/test_results/")
