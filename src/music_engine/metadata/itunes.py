"""iTunes Search API metadata provider."""

from __future__ import annotations

from urllib.parse import urlencode

from .base import MetadataProvider
from .common import TrackMetadata, album_matches, json_get, normalize


class ITunesMetadataProvider(MetadataProvider):
    name = "iTunes Search API"

    def lookup(self, title: str, album: str, artist: str) -> TrackMetadata | None:
        query = urlencode(
            {"term": title, "entity": "song", "country": "in", "limit": 50}
        )
        payload = json_get(f"https://itunes.apple.com/search?{query}")
        candidates = []
        for result in payload.get("results", []):
            result_title = result.get("trackName", "")
            result_album = result.get("collectionName", "")
            if normalize(result_title) != normalize(title) or not album_matches(album, result_album):
                continue
            catalog_artist = result.get("collectionArtistName", "")
            score = 10
            if normalize(catalog_artist) == normalize(artist):
                score += 4
            elif normalize(artist) in normalize(catalog_artist or result.get("artistName", "")):
                score += 2
            candidates.append((score, result))

        if not candidates:
            return None
        result = max(candidates, key=lambda item: item[0])[1]
        date = result.get("releaseDate")
        return TrackMetadata(
            title=result.get("trackName") or title,
            performers=result.get("artistName") or artist,
            album=result.get("collectionName") or album,
            album_artist=result.get("collectionArtistName") or artist,
            date=date[:10] if date else None,
            track_number=result.get("trackNumber"),
            track_count=result.get("trackCount"),
            disc_number=result.get("discNumber"),
            genre=result.get("primaryGenreName"),
            source=self.name,
        )
