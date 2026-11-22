"""Filesystem helpers for a tidy, safe music library."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path


def safe_name(value: str, fallback: str = "Unknown") -> str:
    """Return one filesystem-safe path component while preserving readable names."""
    value = unicodedata.normalize("NFC", value).strip()
    value = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value[:120].rstrip(" .") or fallback)


def track_path(root: Path, artist: str, album: str, title: str) -> Path:
    """Build a predictable artist/album/track destination."""
    return root / safe_name(artist) / safe_name(album) / f"{safe_name(title)}.mp3"
