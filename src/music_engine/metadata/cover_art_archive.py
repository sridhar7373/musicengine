"""MusicBrainz Cover Art Archive artwork provider."""

from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import ArtworkProvider
from .common import TrackMetadata, USER_AGENT
from .musicbrainz import cover_art_url


class CoverArtArchiveProvider(ArtworkProvider):
    name = "MusicBrainz Cover Art Archive"

    def lookup(self, metadata: TrackMetadata, delay: float) -> tuple[bytes, str] | None:
        try:
            image_url = cover_art_url(metadata.album, metadata.album_artist, delay)
        except RuntimeError:
            return None
        if not image_url:
            return None
        request = Request(image_url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=20) as response:
                mime = response.headers.get_content_type()
                if not mime.startswith("image/"):
                    return None
                image = response.read(15 * 1024 * 1024 + 1)
                if len(image) > 15 * 1024 * 1024:
                    return None
                return image, mime
        except (HTTPError, URLError, TimeoutError):
            return None
