"""iTunes Search API metadata provider."""

from __future__ import annotations

import time
from urllib.parse import urlencode

from .base import MetadataProvider
from .common import TrackMetadata, album_matches, json_get, normalize


class ITunesMetadataProvider(MetadataProvider):
    name = "iTunes Search API"

    def lookup(
        self, title: str, album: str, artist: str, delay: float = 1.0
    ) -> TrackMetadata | None:
        failures: list[str] = []
        song_query = urlencode(
            {"term": title, "entity": "song", "country": "in", "limit": 50}
        )
        try:
            payload = json_get(f"https://itunes.apple.com/search?{song_query}")
        except RuntimeError as exc:
            failures.append(str(exc))
        else:
            result = self._find_song(payload.get("results", []), title, album, artist)
            if result:
                return self._metadata(result, title, album, artist)

        if delay:
            time.sleep(delay)
        album_query = urlencode(
            {"term": f"{album} {artist}", "entity": "album", "country": "in", "limit": 50}
        )
        try:
            payload = json_get(f"https://itunes.apple.com/search?{album_query}")
        except RuntimeError as exc:
            failures.append(str(exc))
            raise RuntimeError("; ".join(failures)) from exc

        collections = []
        for result in payload.get("results", []):
            if not album_matches(album, result.get("collectionName", "")):
                continue
            catalog_artist = result.get("artistName", "")
            score = 2 if normalize(catalog_artist) == normalize(artist) else 0
            if normalize(artist) in normalize(catalog_artist):
                score += 1
            collections.append((score, result))
        if not collections:
            if failures:
                raise RuntimeError("; ".join(failures))
            return None

        collection = max(collections, key=lambda item: item[0])[1]
        collection_id = collection.get("collectionId")
        if not collection_id:
            return None
        if delay:
            time.sleep(delay)
        lookup_query = urlencode(
            {"id": collection_id, "entity": "song", "country": "in"}
        )
        try:
            payload = json_get(f"https://itunes.apple.com/lookup?{lookup_query}")
        except RuntimeError as exc:
            raise RuntimeError("; ".join((*failures, str(exc)))) from exc

        result = self._find_song(payload.get("results", []), title, album, artist)
        if not result:
            if failures:
                raise RuntimeError("; ".join(failures))
            return None
        return self._metadata(result, title, album, artist, collection)

    @staticmethod
    def _find_song(results: list[dict], title: str, album: str, artist: str) -> dict | None:
        candidates = []
        for result in results:
            if normalize(result.get("trackName", "")) != normalize(title):
                continue
            if not album_matches(album, result.get("collectionName", "")):
                continue
            catalog_artist = result.get("collectionArtistName") or result.get("artistName", "")
            score = 10
            if normalize(catalog_artist) == normalize(artist):
                score += 4
            elif normalize(artist) in normalize(catalog_artist):
                score += 2
            candidates.append((score, result))
        return max(candidates, key=lambda item: item[0])[1] if candidates else None

    def _metadata(
        self,
        result: dict,
        title: str,
        album: str,
        artist: str,
        collection: dict | None = None,
    ) -> TrackMetadata:
        collection = collection or {}
        date = result.get("releaseDate") or collection.get("releaseDate")
        return TrackMetadata(
            title=result.get("trackName") or title,
            performers=result.get("artistName") or artist,
            album=result.get("collectionName") or album,
            album_artist=(
                result.get("collectionArtistName")
                or collection.get("artistName")
                or artist
            ),
            date=date[:10] if date else None,
            track_number=result.get("trackNumber"),
            track_count=result.get("trackCount") or collection.get("trackCount"),
            disc_number=result.get("discNumber"),
            genre=result.get("primaryGenreName") or collection.get("primaryGenreName"),
            source=self.name,
            artwork_url=result.get("artworkUrl100") or collection.get("artworkUrl100"),
        )
