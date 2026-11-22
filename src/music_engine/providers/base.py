"""Shared provider interface and catalog records."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Album:
    title: str
    url: str


@dataclass(frozen=True)
class Track:
    title: str
    album: str
    url: str


class BaseProvider(ABC):
    """Contract implemented by each catalog/download source."""

    name = "Provider"

    @classmethod
    @abstractmethod
    def supports(cls, url: str) -> bool:
        """Return whether this provider owns the URL's host and page format."""

    @abstractmethod
    def resolve_artist_url(self, artist_name: str, delay: float = 1.0) -> str:
        """Find an artist's discography page from a display name."""

    @abstractmethod
    def artist_albums(
        self, artist_url: str, delay: float = 0.25
    ) -> tuple[str, list[Album]]:
        """Return the artist name and its albums, including paginated results."""

    @abstractmethod
    def album_tracks(self, album: Album, delay: float = 0.25) -> list[Track]:
        """Return the downloadable tracks listed on an album page."""

    @abstractmethod
    def download_track(
        self,
        track: Track,
        destination: Path,
        progress: Callable[[int, int | None], None] | None = None,
    ) -> int:
        """Download a track and return its size in bytes."""
