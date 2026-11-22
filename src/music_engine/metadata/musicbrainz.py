"""MusicBrainz metadata provider and release matching helpers."""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlencode

from .base import MetadataProvider
from .common import TrackMetadata, album_matches, credit_name, json_get, normalize


class MusicBrainzMetadataProvider(MetadataProvider):
    name = "MusicBrainz"

    def lookup(self, title: str, album: str, artist: str) -> TrackMetadata | None:
        query = f'recording:"{title}" AND release:"{album}" AND artist:"{artist}"'
        params = urlencode({"query": query, "fmt": "json", "limit": 10, "inc": "releases"})
        payload = json_get(f"https://musicbrainz.org/ws/2/recording/?{params}")
        expected_title = normalize(title)
        expected_artist = normalize(artist)
        candidates = []
        for recording in payload.get("recordings", []):
            if normalize(recording.get("title", "")) != expected_title:
                continue
            performers = credit_name(recording.get("artist-credit", [])) or artist
            for release in recording.get("releases", []):
                if not album_matches(album, release.get("title", "")):
                    continue
                album_artist = credit_name(release.get("artist-credit", [])) or artist
                score = 10 + (4 if expected_artist in normalize(album_artist) else 0)
                candidates.append((score, recording, release, performers, album_artist))
        if not candidates:
            return None

        _, recording, release, performers, album_artist = max(
            candidates, key=lambda item: item[0]
        )
        return TrackMetadata(
            title=recording.get("title") or title,
            performers=performers,
            album=release.get("title") or album,
            album_artist=album_artist,
            date=release.get("date"),
            source=self.name,
        )


@lru_cache(maxsize=128)
def cover_art_url(album: str, artist: str, delay: float) -> str | None:
    """Resolve a release's front image URL through MusicBrainz and CAA."""
    query = f'release:"{album}" AND artist:"{artist}"'
    params = urlencode({"query": query, "fmt": "json", "limit": 10})
    payload = json_get(f"https://musicbrainz.org/ws/2/release/?{params}")
    matches = []
    for release in payload.get("releases", []):
        if not album_matches(album, release.get("title", "")):
            continue
        credit = normalize(credit_name(release.get("artist-credit", [])))
        if normalize(artist) not in credit:
            continue
        score = 1 + (3 if release.get("country") == "IN" else 0)
        matches.append((score, release))
    if not matches:
        return None

    release_id = max(matches, key=lambda item: item[0])[1].get("id")
    if not release_id:
        return None
    if delay:
        import time

        time.sleep(delay)
    cover_data = json_get(f"https://coverartarchive.org/release/{release_id}")
    front = next((image for image in cover_data.get("images", []) if image.get("front")), None)
    if not front:
        return None
    image_url = front.get("thumbnails", {}).get("500") or front.get("image")
    if image_url and image_url.startswith("http://"):
        image_url = "https://" + image_url[len("http://"):]
    return image_url
