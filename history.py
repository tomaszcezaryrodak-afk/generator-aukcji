"""
Historia generowan aukcji.

Zapisuje i odczytuje generowane aukcje w formacie JSON Lines.
"""

import json
from pathlib import Path
from datetime import datetime

HISTORY_DIR = Path(__file__).parent / "output"
HISTORY_FILE = HISTORY_DIR / "generations.jsonl"
MAX_ENTRIES = 500


def save_generation(title="", sku="", catalog="", kategoria="",
                    bl_product_id=None, timestamp="", description_html="",
                    images_count=0, extra_data=None):
    """Zapisuje generowanie do historii (JSON Lines).

    Args:
        title: tytul aukcji
        sku: kod SKU
        catalog: nazwa katalogu
        kategoria: kategoria produktu
        bl_product_id: ID produktu w BaseLinker (None jesli nie wyslano)
        timestamp: timestamp generowania
        description_html: opis HTML
        images_count: liczba wygenerowanych grafik
        extra_data: dodatkowe dane (dict)
    """
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": timestamp or datetime.now().strftime("%Y%m%d_%H%M%S"),
        "title": title,
        "sku": sku,
        "catalog": catalog,
        "kategoria": kategoria,
        "bl_product_id": bl_product_id,
        "images_count": images_count,
        "created_at": datetime.now().isoformat(),
    }
    if extra_data:
        entry["extra"] = extra_data

    # Append do pliku
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Rotacja: max MAX_ENTRIES
    _rotate_history()


def _rotate_history():
    """Utrzymuje max MAX_ENTRIES wpisow."""
    if not HISTORY_FILE.exists():
        return
    lines = HISTORY_FILE.read_text(encoding="utf-8").strip().split("\n")
    if len(lines) > MAX_ENTRIES:
        lines = lines[-MAX_ENTRIES:]
        HISTORY_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_history():
    """Wczytuje historie generowan. Zwraca liste dict od najnowszego."""
    if not HISTORY_FILE.exists():
        return []
    entries = []
    for line in HISTORY_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    entries.reverse()
    return entries[:MAX_ENTRIES]


def cleanup_old_outputs(output_dir, max_files=50):
    """Usuwa najstarsze pliki ZIP z output/, zachowujac max_files."""
    if not output_dir.exists():
        return
    zips = sorted(output_dir.glob("aukcja_*.zip"), key=lambda p: p.stat().st_mtime)
    while len(zips) > max_files:
        oldest = zips.pop(0)
        try:
            oldest.unlink()
        except OSError:
            pass
