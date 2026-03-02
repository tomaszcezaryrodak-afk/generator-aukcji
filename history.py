"""
Historia generowań aukcji + system szkiców aukcji.

Zapisuje i odczytuje generowane aukcje w formacie JSON Lines.
System szkiców: pełne dane aukcji (grafiki base64, opis, specyfikacja) w osobnych JSON.
"""

import json
import re
from pathlib import Path
from datetime import datetime

HISTORY_DIR = Path(__file__).parent / "output"
HISTORY_FILE = HISTORY_DIR / "generations.jsonl"
AUCTION_DIR = HISTORY_DIR / "history"
INDEX_FILE = AUCTION_DIR / "index.jsonl"
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
        bl_product_id: ID produktu w BaseLinker (None jeśli nie wysłano)
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
    """Utrzymuje max MAX_ENTRIES wpisów."""
    if not HISTORY_FILE.exists():
        return
    lines = HISTORY_FILE.read_text(encoding="utf-8").strip().split("\n")
    if len(lines) > MAX_ENTRIES:
        lines = lines[-MAX_ENTRIES:]
        HISTORY_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_history():
    """Wczytuje historię generowań. Zwraca listę dict od najnowszego."""
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
    """Usuwa najstarsze pliki ZIP z output/, zachowując max_files."""
    if not output_dir.exists():
        return
    zips = sorted(output_dir.glob("aukcja_*.zip"), key=lambda p: p.stat().st_mtime)
    while len(zips) > max_files:
        oldest = zips.pop(0)
        try:
            oldest.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# System szkicow aukcji (pelne dane z grafikami)
# ---------------------------------------------------------------------------

def _make_auction_id(kategoria: str) -> str:
    """Tworzy ID aukcji: data_godzina_slug."""
    now = datetime.now()
    slug = re.sub(r'[^\w]+', '-', kategoria.lower())[:30].strip('-')
    return f"{now.strftime('%Y-%m-%d_%H%M%S')}_{slug}"


def save_auction(data: dict, status: str = "szkic", auction_id: str | None = None) -> str:
    """Zapisuje aukcje do historii. Zwraca ID.

    data: dict z kluczami: kategoria, kolory, grafiki (base64), opis, specyfikacja.
    status: 'szkic' lub 'wysłany'.
    auction_id: opcjonalny ID do nadpisania (upsert). None = nowy wpis.
    """
    AUCTION_DIR.mkdir(parents=True, exist_ok=True)
    if auction_id is None:
        kategoria = data.get("kategoria", "produkt")
        auction_id = _make_auction_id(kategoria)

    auction = {
        "id": auction_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        **data,
    }

    path = AUCTION_DIR / f"{auction_id}.json"
    path.write_text(json.dumps(auction, ensure_ascii=False, indent=2), encoding="utf-8")

    # FIX-13: Upsert metadanych w index.jsonl (usuń stary wpis przed append)
    index_entry = {
        "id": auction_id,
        "created_at": auction["created_at"],
        "kategoria": data.get("kategoria", ""),
        "status": status,
    }
    if INDEX_FILE.exists():
        try:
            lines = INDEX_FILE.read_text(encoding="utf-8").strip().split("\n")
            lines = [l for l in lines if l.strip() and json.loads(l).get("id") != auction_id]
            INDEX_FILE.write_text("\n".join(lines) + "\n" if lines else "", encoding="utf-8")
        except (json.JSONDecodeError, OSError):
            pass
    with open(INDEX_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(index_entry, ensure_ascii=False) + "\n")

    return auction_id


def load_auction(auction_id: str) -> dict:
    """Wczytuje aukcje z historii. Zwraca dict lub pusty dict."""
    path = AUCTION_DIR / f"{auction_id}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def list_auctions() -> list:
    """Lista aukcji (id, created_at, kategoria, status). Sortowane od najnowszej.

    FIX-13: Czyta z INDEX_FILE zamiast skanowania JSON-ów.
    Fallback na pełny skan gdy index nie istnieje lub jest desynchronizowany.
    """
    if not AUCTION_DIR.exists():
        return []

    json_count = len(list(AUCTION_DIR.glob("*.json")))
    if json_count == 0:
        return []

    # Próba odczytu z indeksu
    if INDEX_FILE.exists():
        auctions = []
        for line in INDEX_FILE.read_text(encoding="utf-8").strip().split("\n"):
            if not line.strip():
                continue
            try:
                auctions.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        # Desync check: index ma mniej wpisów niż plików JSON
        if len(auctions) >= json_count:
            auctions.sort(key=lambda a: a.get("created_at", ""), reverse=True)
            return auctions

    # Fallback / rebuild: index brakuje lub desync
    return _rebuild_index()


def update_auction_status(auction_id: str, status: str):
    """Zmienia status aukcji (szkic / wysłany). Aktualizuje też INDEX_FILE."""
    path = AUCTION_DIR / f"{auction_id}.json"
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = status
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except (json.JSONDecodeError, OSError):
        return

    # FIX-13: Aktualizuj INDEX_FILE (przepisz linię z nowym statusem)
    if INDEX_FILE.exists():
        try:
            lines = INDEX_FILE.read_text(encoding="utf-8").strip().split("\n")
            updated_lines = []
            for line in lines:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("id") == auction_id:
                        entry["status"] = status
                    updated_lines.append(json.dumps(entry, ensure_ascii=False))
                except json.JSONDecodeError:
                    updated_lines.append(line)
            INDEX_FILE.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
        except OSError:
            pass


def _rebuild_index() -> list:
    """Skanuje JSON-y i odbudowuje INDEX_FILE. Zwraca listę aukcji."""
    if not AUCTION_DIR.exists():
        return []
    auctions = []
    for path in AUCTION_DIR.glob("*.json"):
        if path.name == "index.jsonl":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            auctions.append({
                "id": data.get("id", path.stem),
                "created_at": data.get("created_at", ""),
                "kategoria": data.get("kategoria", ""),
                "status": data.get("status", "szkic"),
            })
        except (json.JSONDecodeError, OSError):
            continue
    auctions.sort(key=lambda a: a.get("created_at", ""), reverse=True)
    # Zapisz odbudowany index
    try:
        lines = [json.dumps(a, ensure_ascii=False) for a in auctions]
        INDEX_FILE.write_text("\n".join(lines) + "\n" if lines else "", encoding="utf-8")
    except OSError:
        pass
    return auctions


def export_all_auctions() -> bytes | None:
    """Eksportuje wszystkie aukcje jako ZIP z JSON-ami. Zwraca bytes lub None."""
    import io
    import zipfile
    if not AUCTION_DIR.exists():
        return None
    jsons = list(AUCTION_DIR.glob("*.json"))
    if not jsons:
        return None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for path in jsons:
            zf.write(path, f"aukcje/{path.name}")
    buf.seek(0)
    return buf.getvalue()
