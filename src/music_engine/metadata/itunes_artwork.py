"""Download album artwork from the matched iTunes Search API result."""

from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .base import ArtworkProvider
from .common import TrackMetadata, USER_AGENT


class ITunesArtworkProvider(ArtworkProvider):
    name = "iTunes Search API artwork"

    def lookup(self, metadata: TrackMetadata, delay: float) -> tuple[bytes, str] | None:
        if not metadata.artwork_url:
            return None

        parts = urlsplit(metadata.artwork_url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            return None

        path = parts.path.replace("100x100", "600x600")
        image_url = urlunsplit(("https", parts.netloc, path, parts.query, parts.fragment))
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
