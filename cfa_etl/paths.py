from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DERIVED_DIR = ROOT / "data" / "derived"
CONFIG_DIR = ROOT / "config"

COMMENTS_API = "https://crossfitsouthbrooklyn.com/wp-json/wp/v2/comments"

