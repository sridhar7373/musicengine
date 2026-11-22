"""Metadata provider waterfall and artwork provider selection."""

from __future__ import annotations

import time

from .base import ArtworkProvider, MetadataProvider
from .common import MetadataNotFound, TrackMetadata
from .cover_art_archive import CoverArtArchiveProvider
from .itunes import ITunesMetadataProvider
from .musicbrainz import MusicBrainzMetadataProvider


METADATA_PROVIDERS: tuple[type[MetadataProvider], ...] = (
    ITunesMetadataProvider,
    MusicBrainzMetadataProvider,
)
ARTWORK_PROVIDERS: tuple[type[ArtworkProvider], ...] = (CoverArtArchiveProvider,)


def find_track_metadata(
    title: str, album: str, artist: str, delay: float = 1.0
) -> TrackMetadata:
    """Try registered metadata sources in order and return the first match."""
    failures = []
    for index, provider_type in enumerate(METADATA_PROVIDERS):
        try:
            result = provider_type().lookup(title, album, artist)
        except RuntimeError as exc:
            failures.append(str(exc))
            result = None
        if result is not None:
            return result
        if delay and index < len(METADATA_PROVIDERS) - 1:
            time.sleep(delay)
    if failures:
        raise RuntimeError("Metadata catalogs unavailable: " + "; ".join(failures))
    raise MetadataNotFound(f"No catalog match for {title!r} from {album!r}.")


def get_cover_art(album: str, artist: str, delay: float = 1.0) -> tuple[bytes, str] | None:
    """Try registered artwork sources in order."""
    for index, provider_type in enumerate(ARTWORK_PROVIDERS):
        try:
            result = provider_type().lookup(album, artist, delay)
        except RuntimeError:
            result = None
        if result:
            return result
        if delay and index < len(ARTWORK_PROVIDERS) - 1:
            time.sleep(delay)
    return None


__all__ = [
    "ARTWORK_PROVIDERS",
    "METADATA_PROVIDERS",
    "ArtworkProvider",
    "MetadataNotFound",
    "MetadataProvider",
    "TrackMetadata",
    "find_track_metadata",
    "get_cover_art",
]
