#!/usr/bin/env python3
"""
Skrypt uruchamiajacy trening LoRA via FAL.AI.
Uzycie: .venv/bin/python3 run_lora_training.py
Szacowany koszt: ~$8.00 (1000 krokow x $0.008/krok)
Szacowany czas: 15-30 min
"""
import asyncio
import logging
import os
import sys

# Wczytaj .env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

# Ustaw FAL_KEY
fal_key = os.environ.get("FAL_AI_API_KEY", "")
if not fal_key:
    print("BLAD: Brak FAL_AI_API_KEY w .env")
    sys.exit(1)
os.environ["FAL_KEY"] = fal_key

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

from lora_training import LoRATrainer, LoRAConfig


async def main():
    steps = 1000
    config = LoRAConfig(steps=steps)
    trainer = LoRATrainer(config)

    # Etap 1: Przygotowanie datasetu
    logger.info("=== ETAP 1: Przygotowanie datasetu ===")
    from pathlib import Path
    dataset_url = trainer.prepare_dataset(Path("training"))
    logger.info(f"Dataset URL: {dataset_url[:80]}...")

    # Etap 2: Trening
    logger.info(f"=== ETAP 2: Trening ({steps} krokow, ~${steps * 0.008:.2f}) ===")
    result = await trainer.train(dataset_url)

    lora_url = ""
    if isinstance(result, dict):
        lora_url = result.get("diffusers_lora_file", {}).get("url", "")
    if not lora_url:
        logger.error("Trening nie zwrocil URL do LoRA")
        logger.error(f"Result: {result}")
        sys.exit(1)

    logger.info(f"LoRA URL: {lora_url}")

    # Etap 3: Zapisz wersje
    logger.info("=== ETAP 3: Zapisanie wersji ===")
    version = await trainer.save_version(lora_url, {"quality_gate": False, "steps": steps})
    logger.info(f"Zapisano jako {version}")

    # Etap 4: Quality gate (generowanie testowych obrazow)
    logger.info("=== ETAP 4: Quality gate ===")
    validation = await trainer.validate(lora_url)
    logger.info(f"Wyniki walidacji: {validation.get('test_count', 0)} testow")
    logger.info(f"Obrazy testowe w: training/lora_versions/test_results/")

    # Podsumowanie
    logger.info("=== PODSUMOWANIE ===")
    logger.info(f"Wersja: {version}")
    logger.info(f"LoRA URL: {lora_url}")
    logger.info(f"Koszt: ~${steps * 0.008:.2f}")
    logger.info(f"Quality gate: wymaga manualnej weryfikacji")

    # Zapisz URL do pliku
    with open("training/lora_versions/latest_lora_url.txt", "w") as f:
        f.write(lora_url)
    logger.info("URL zapisany w training/lora_versions/latest_lora_url.txt")

    return {"version": version, "lora_url": lora_url, "cost_usd": steps * 0.008}


if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\nGOTOWE: {result}")
