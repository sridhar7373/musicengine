"""Shared data types and catalog matching helpers."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_AGENT = "MusicEngine/0.1.0 (personal music library)"


class MetadataNotFound(RuntimeError):
    """No confident catalog match was found for a track."""


@dataclass(frozen=True)
class TrackMetadata:
    title: str
    performers: str
    album: str
    album_artist: str
    date: str | None = None
    track_number: int | None = None
    track_count: int | None = None
    disc_number: int | None = None
    genre: str | None = None
    source: str = ""
    artwork_url: str | None = None


def json_get(url: str) -> dict:
    request = Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Catalog request failed: {exc}") from exc


def normalize(value: str) -> str:
    value = value.casefold()
    value = re.sub(r"\b(original\s+)?(motion\s+picture\s+)?soundtrack\b", "", value)
    value = re.sub(r"\bmp3\b", "", value)
    return "".join(character for character in value if character.isalnum())


def album_matches(expected: str, actual: str) -> bool:
    """Match normalized album titles, allowing small transliteration variants."""
    expected_name, actual_name = normalize(expected), normalize(actual)
    return bool(
        expected_name
        and actual_name
        and (
            expected_name == actual_name
            or actual_name.startswith(expected_name)
            or (
                min(len(expected_name), len(actual_name)) >= 10
                and SequenceMatcher(None, expected_name, actual_name).ratio() >= 0.9
            )
        )
    )


def title_matches(expected: str, actual: str) -> bool:
    """Match song-title transliterations while rejecting short vague names."""
    expected_name, actual_name = normalize(expected), normalize(actual)
    return bool(
        expected_name
        and actual_name
        and (
            expected_name == actual_name
            or (
                min(len(expected_name), len(actual_name)) >= 8
                and SequenceMatcher(None, expected_name, actual_name).ratio() >= 0.84
            )
        )
    )


def credit_name(credit: list[dict]) -> str:
    pieces = []
    for item in credit:
        pieces.append(item.get("name") or item.get("artist", {}).get("name", ""))
        pieces.append(item.get("joinphrase", ""))
    return "".join(pieces).strip()
