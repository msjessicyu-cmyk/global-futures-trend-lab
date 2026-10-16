"""Small presentation helpers."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

def load_markets() -> list[dict]:
    return json.loads((ROOT / "config" / "markets.json").read_text(encoding="utf-8"))
