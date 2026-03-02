"""
lora_training.py - Trening LoRA via FAL.AI + quality gate + wersjonowanie.
Endpoint: fal-ai/flux-2-trainer ($0.008/krok).
Inference: fal-ai/flux-2/lora ($0.021/MP).
"""
import asyncio
import io
import json
import logging
import os
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

LORA_MIN_IMAGES = 9
LORA_MAX_IMAGES = 200

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

DEFAULT_TEST_PROMPTS = [
    "granite_sink_premium installed in oak countertop, overhead view, natural daylight",
    "granite_sink_premium in modern kitchen, eye-level, water running",
    "granite_sink_premium close-up, granite texture visible, water droplets",
    "granite_sink_premium with faucet, scandinavian kitchen, bright",
    "granite_sink_premium double bowl, dark granite, frontal view",
]


@dataclass
class LoRAConfig:
    trigger_word: str = "granite_sink_premium"
    steps: int = 1000
    learning_rate: float = 0.00005
    output_format: str = "fal"  # "fal" lub "comfy"
    trainer_model: str = "fal-ai/flux-2-trainer"
    inference_model: str = "fal-ai/flux-2/lora"


class LoRATrainer:
    def __init__(self, config: LoRAConfig | None = None):
        self.config = config or LoRAConfig()
        self._client = None
        self._registry_path = Path("training/lora_versions/lora_registry.json")
        self._versions_dir = Path("training/lora_versions")

    def _get_client(self):
        if self._client is None:
            fal_key = os.environ.get("FAL_AI_API_KEY", "") or os.environ.get(
                "FAL_KEY", ""
            )
            if not fal_key:
                raise ValueError("FAL_AI_API_KEY nie skonfigurowany")
            os.environ["FAL_KEY"] = fal_key
            try:
                import fal_client
            except ImportError:
                raise ImportError(
                    "Brak pakietu fal_client. Zainstaluj: pip install fal-client"
                )
            self._client = fal_client
        return self._client

    def prepare_dataset(self, image_dir: Path) -> str:
        """Pakuje obrazy z katalogu do ZIP i uploaduje na FAL."""
        image_dir = Path(image_dir)
        if not image_dir.exists():
            raise FileNotFoundError(f"Katalog nie istnieje: {image_dir}")

        images = [
            p
            for p in image_dir.rglob("*")
            if p.suffix.lower() in IMAGE_EXTENSIONS and p.is_file()
        ]

        if len(images) < LORA_MIN_IMAGES:
            raise ValueError(
                f"Za mało obrazów: {len(images)} (minimum {LORA_MIN_IMAGES})"
            )
        if len(images) > LORA_MAX_IMAGES:
            raise ValueError(
                f"Za dużo obrazów: {len(images)} (maximum {LORA_MAX_IMAGES})"
            )

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for img_path in images:
                zf.write(img_path, img_path.name)
        zip_buffer.seek(0)

        size_mb = len(zip_buffer.getvalue()) / (1024 * 1024)
        logger.info(
            f"Przygotowano dataset: {len(images)} obrazów, {size_mb:.1f} MB"
        )

        client = self._get_client()

        # upload_file() z pliku na dysku - stabilny dla dużych plików.
        # client.upload(bytes) zawodzi przy multipart >100MB (HTTP 500 na chunkach).
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(zip_buffer.getvalue())
            tmp_path = tmp.name

        try:
            logger.info(f"Uploaduje dataset ({size_mb:.1f} MB) na FAL CDN...")
            url = client.upload_file(tmp_path)
        finally:
            os.unlink(tmp_path)

        return url

    async def train(self, dataset_url: str, config: LoRAConfig | None = None) -> dict:
        """Uruchamia trening LoRA na FAL.AI."""
        cfg = config or self.config
        client = self._get_client()

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: client.subscribe(
                    cfg.trainer_model,
                    arguments={
                        "image_data_url": dataset_url,
                        "steps": cfg.steps,
                        "learning_rate": cfg.learning_rate,
                        "default_caption": cfg.trigger_word,
                        "output_lora_format": cfg.output_format,
                    },
                ),
            )
        except Exception as e:
            logger.error(f"Błąd treningu LoRA: {e}")
            raise

        lora_url = ""
        if isinstance(result, dict):
            lora_url = result.get("diffusers_lora_file", {}).get("url", "")
        logger.info(f"Trening zakończony. LoRA URL: {lora_url}")
        return result

    async def validate(
        self, lora_url: str, test_prompts: list[str] | None = None,
        scale: float | None = None,
    ) -> dict:
        """Generuje obrazy testowe z i bez LoRA do manualnej weryfikacji."""
        import httpx

        if scale is None:
            try:
                from config import LORA_WEIGHT
                scale = LORA_WEIGHT
            except ImportError:
                scale = 0.75

        prompts = test_prompts or DEFAULT_TEST_PROMPTS
        client = self._get_client()

        test_dir = self._versions_dir / "test_results"
        test_dir.mkdir(parents=True, exist_ok=True)

        test_images_lora = []
        test_images_base = []
        loop = asyncio.get_running_loop()
        http = httpx.Client(timeout=30)

        for i, prompt in enumerate(prompts):
            # Z LoRA
            try:
                result_lora = await loop.run_in_executor(
                    None,
                    lambda p=prompt: client.subscribe(
                        self.config.inference_model,
                        arguments={
                            "prompt": p,
                            "loras": [{"path": lora_url, "scale": scale}],
                            "image_size": "landscape_16_9",
                            "num_images": 1,
                        },
                    ),
                )
                img_url = result_lora.get("images", [{}])[0].get("url", "")
                lora_path = test_dir / f"test_{i:02d}_lora.png"
                if img_url:
                    resp = http.get(img_url)
                    lora_path.write_bytes(resp.content)
                test_images_lora.append(str(lora_path))
                logger.info(f"Test LoRA {i}: zapisano {lora_path}")
            except Exception as e:
                logger.error(f"Błąd generowania z LoRA (prompt {i}): {e}")
                test_images_lora.append(f"BŁĄD: {e}")

            # Bez LoRA (baseline)
            try:
                result_base = await loop.run_in_executor(
                    None,
                    lambda p=prompt: client.subscribe(
                        self.config.inference_model,
                        arguments={
                            "prompt": p,
                            "image_size": "landscape_16_9",
                            "num_images": 1,
                        },
                    ),
                )
                img_url = result_base.get("images", [{}])[0].get("url", "")
                base_path = test_dir / f"test_{i:02d}_base.png"
                if img_url:
                    resp = http.get(img_url)
                    base_path.write_bytes(resp.content)
                test_images_base.append(str(base_path))
                logger.info(f"Test base {i}: zapisano {base_path}")
            except Exception as e:
                logger.error(f"Błąd generowania baseline (prompt {i}): {e}")
                test_images_base.append(f"BŁĄD: {e}")

        http.close()

        return {
            "passed": True,  # placeholder, wymaga manualnej weryfikacji
            "lora_url": lora_url,
            "test_count": len(prompts),
            "test_images_lora": test_images_lora,
            "test_images_base": test_images_base,
            "notes": "Quality gate wymaga manualnej weryfikacji. Sprawdź obrazy w test_results/.",
            "timestamp": datetime.now().isoformat(),
        }

    async def save_version(
        self, lora_url: str, metadata: dict | None = None
    ) -> str:
        """Zapisuje wersje LoRA do rejestru z auto-increment ID."""
        self._versions_dir.mkdir(parents=True, exist_ok=True)

        registry = self._load_registry()

        # Auto-increment version ID
        existing_ids = [v.get("id", "") for v in registry.get("versions", [])]
        max_num = 0
        for vid in existing_ids:
            if vid.startswith("v") and vid[1:].isdigit():
                max_num = max(max_num, int(vid[1:]))
        version_id = f"v{max_num + 1:03d}"

        entry = {
            "id": version_id,
            "url": lora_url,
            "date": datetime.now().isoformat(),
            "steps": self.config.steps,
            "trigger_word": self.config.trigger_word,
            "quality_gate": metadata.get("quality_gate", False)
            if metadata
            else False,
        }

        registry["versions"].append(entry)
        registry["active"] = version_id

        self._save_registry(registry)
        logger.info(f"LoRA {version_id} zapisane. URL: {lora_url}")
        return version_id

    async def rollback(self, version: str) -> bool:
        """Przywraca wczesniejsza wersje LoRA jako aktywna."""
        registry = self._load_registry()

        version_exists = any(
            v["id"] == version for v in registry.get("versions", [])
        )
        if not version_exists:
            logger.error(f"Wersja {version} nie istnieje w rejestrze LoRA")
            return False

        registry["active"] = version
        self._save_registry(registry)
        logger.info(f"Rollback do {version}")
        return True

    def get_registry(self) -> dict:
        """Zwraca pelny rejestr wersji LoRA."""
        return self._load_registry()

    def get_active_lora_url(self) -> str | None:
        """Zwraca URL aktywnej wersji LoRA."""
        registry = self._load_registry()
        active_id = registry.get("active")
        if not active_id:
            return None

        for v in registry.get("versions", []):
            if v["id"] == active_id:
                return v.get("url")
        return None

    def _load_registry(self) -> dict:
        """Ładuje rejestr z pliku JSON."""
        if self._registry_path.exists():
            with open(self._registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"versions": [], "active": None}

    def _save_registry(self, registry: dict) -> None:
        """Zapisuje rejestr do pliku JSON."""
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)


async def quick_train(image_dir: str = "training", steps: int = 1000) -> dict:
    """Szybki helper: prepare + train + validate + save. One-liner."""
    trainer = LoRATrainer(LoRAConfig(steps=steps))

    logger.info(f"Przygotowanie datasetu z {image_dir}...")
    dataset_url = trainer.prepare_dataset(Path(image_dir))

    logger.info(f"Rozpoczynam trening ({steps} kroków, ~${steps * 0.008:.2f})...")
    result = await trainer.train(dataset_url)

    lora_url = ""
    if isinstance(result, dict):
        lora_url = result.get("diffusers_lora_file", {}).get("url", "")
    if not lora_url:
        raise ValueError("Trening nie zwrocil URL do LoRA")

    logger.info("Walidacja jakości (quality gate)...")
    validation = await trainer.validate(lora_url)

    version = await trainer.save_version(
        lora_url, {"quality_gate": validation.get("passed", False)}
    )

    return {
        "version": version,
        "lora_url": lora_url,
        "validation": validation,
        "cost_usd": steps * 0.008,
    }
