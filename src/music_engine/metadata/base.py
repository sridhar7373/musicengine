"""Base interfaces for metadata and artwork providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .common import TrackMetadata


class MetadataProvider(ABC):
    """Catalog source that can identify a track and its tags."""

    name = "Metadata provider"

    @abstractmethod
    def lookup(self, title: str, album: str, artist: str) -> TrackMetadata | None:
        """Return a confident match, or None when this source has no match."""


class ArtworkProvider(ABC):
    """Source for a matching album front cover."""

    name = "Artwork provider"

    @abstractmethod
    def lookup(self, album: str, artist: str, delay: float) -> tuple[bytes, str] | None:
        """Return image bytes and MIME type, or None when no cover is available."""
