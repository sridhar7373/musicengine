"""Small persistent user settings for the CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile


def settings_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    root = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    return root / "music-engine" / "config.json"


def load_default_artist() -> str | None:
    path = settings_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read settings file {path}: {exc}") from exc
    artist = data.get("default_artist") if isinstance(data, dict) else None
    return artist.strip() if isinstance(artist, str) and artist.strip() else None


def save_default_artist(artist: str) -> Path:
    artist = artist.strip()
    if not artist:
        raise ValueError("Artist name cannot be empty.")

    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=".config.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump({"default_artist": artist}, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
        temporary_path.replace(path)
    except OSError:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    return path
