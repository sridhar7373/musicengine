"""Isaimini implementation of the music provider interface."""

from __future__ import annotations

import codecs
from html.parser import HTMLParser
from pathlib import Path
import re
import tempfile
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from .base import Album, BaseProvider, Track


BASE_HOSTS = {"isaimini.mobile", "www.isaimini.mobile"}
DIRECTORY_URL = "https://www.isaimini.mobile/tamil-music-directors-discography/"
USER_AGENT = "music-engine/0.1 (+personal music library)"
_VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


def _clean_text(parts: list[str]) -> str:
    return " ".join("".join(parts).split())


class _PageParser(HTMLParser):
    """Collect only page metadata and relevant links while parsing incrementally."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, set[str]]] = []
        self.heading_parts: list[str] | None = None
        self.heading = ""
        self.anchor: dict[str, object] | None = None
        self.album_links: list[tuple[str, str]] = []
        self.artist_links: list[tuple[str, str]] = []
        self.pagination_links: list[str] = []
        self.download_links: list[tuple[str, str]] = []

    def _start(self, tag: str, attrs) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "h1":
            self.heading_parts = []
        elif tag == "a":
            ancestor_classes = set().union(*(item[1] for item in self.stack)) if self.stack else set()
            self.anchor = {
                "href": attributes.get("href"),
                "title": attributes.get("title") or "",
                "parts": [],
                "album": "album-title" in ancestor_classes,
                "artist": "side-bar" in ancestor_classes,
                "pagination": "pagination-box" in ancestor_classes,
                "download": "downloadbutton" in classes,
            }
        if tag not in _VOID_TAGS:
            self.stack.append((tag, classes))

    def handle_starttag(self, tag: str, attrs) -> None:
        self._start(tag, attrs)

    def handle_startendtag(self, tag: str, attrs) -> None:
        self._start(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self.heading_parts is not None:
            self.heading_parts.append(data)
        if self.anchor is not None:
            self.anchor["parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.anchor is not None:
            self._finish_anchor()
        if tag == "h1" and self.heading_parts is not None:
            self.heading = _clean_text(self.heading_parts)
            self.heading_parts = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def _finish_anchor(self) -> None:
        anchor = self.anchor
        self.anchor = None
        href = anchor["href"]
        if not href:
            return
        title = _clean_text(anchor["parts"])
        if anchor["album"] and title:
            self.album_links.append((title, href))
        if anchor["artist"] and title:
            self.artist_links.append((title, href))
        if anchor["pagination"]:
            self.pagination_links.append(href)
        if anchor["download"]:
            label = anchor["title"] or title
            self.download_links.append((href, label))


def _checked_page_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in BASE_HOSTS:
        raise ValueError("Use an Isaimini artist or album page URL on isaimini.mobile.")
    return url


def _fetch_page(url: str, timeout: float = 30) -> _PageParser:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    parser = _PageParser()
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    try:
        with urlopen(request, timeout=timeout) as response:
            while chunk := response.read(64 * 1024):
                parser.feed(decoder.decode(chunk))
            parser.feed(decoder.decode(b"", final=True))
            parser.close()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not fetch {url}: {exc}") from exc
    return parser


def _title_from_heading(heading: str, fallback: str) -> str:
    match = re.search(r"\s+(?:mp3\s+)?songs?\s+download\b", heading, re.IGNORECASE)
    return (heading[:match.start()] if match else heading).strip() or fallback


class IsaiminiProvider(BaseProvider):
    name = "Isaimini"

    @classmethod
    def supports(cls, url: str) -> bool:
        return urlparse(url).hostname in BASE_HOSTS

    def resolve_artist_url(self, artist_name: str, delay: float = 1.0) -> str:
        """Look up a music director's page from Isaimini's directory."""
        page = _fetch_page(DIRECTORY_URL)
        if delay:
            time.sleep(delay)
        requested = " ".join(artist_name.casefold().split())
        matches = [
            href
            for title, href in page.artist_links
            if " ".join(title.casefold().split()) == requested
        ]
        if not matches:
            available = ", ".join(title for title, _ in page.artist_links)
            raise ValueError(
                f"Artist {artist_name!r} was not found in the Isaimini directory. "
                f"Available names: {available}"
            )
        return urljoin(DIRECTORY_URL, matches[0])

    def artist_albums(
        self, artist_url: str, delay: float = 0.25
    ) -> tuple[str, list[Album]]:
        """Collect album links across the artist page's pagination."""
        first_url = _checked_page_url(artist_url)
        artist_name = "Artist"
        albums: list[Album] = []
        seen_pages: set[str] = set()
        seen_albums: set[str] = set()
        pending = [first_url]

        while pending:
            page_url = pending.pop(0)
            if page_url in seen_pages:
                continue
            seen_pages.add(page_url)
            page = _fetch_page(page_url)
            artist_name = _title_from_heading(page.heading, artist_name)

            for title, href in page.album_links:
                absolute = urljoin(page_url, href)
                if urlparse(absolute).hostname not in BASE_HOSTS:
                    continue
                if absolute not in seen_albums:
                    seen_albums.add(absolute)
                    albums.append(Album(title, absolute))

            for href in page.pagination_links:
                page_link = urljoin(page_url, href)
                if (
                    urlparse(page_link).hostname in BASE_HOSTS
                    and page_link not in seen_pages
                    and page_link not in pending
                ):
                    pending.append(page_link)
            if delay:
                time.sleep(delay)

        return artist_name, albums

    def album_tracks(self, album: Album, delay: float = 0.25) -> list[Track]:
        page = _fetch_page(_checked_page_url(album.url))
        actual_album = _title_from_heading(page.heading, album.title)
        tracks: list[Track] = []
        seen: set[str] = set()
        for href, label in page.download_links:
            match = re.search(r"Download\s+(.+?)\s+Song\b", label, re.IGNORECASE)
            title = match.group(1).strip() if match else label.strip()
            absolute = urljoin(album.url, href)
            parsed = urlparse(absolute)
            if (
                parsed.hostname in BASE_HOSTS
                and parsed.path.startswith("/download/")
                and absolute not in seen
                and title
            ):
                seen.add(absolute)
                tracks.append(Track(title, actual_album, absolute))
        if delay:
            time.sleep(delay)
        return tracks

    def download_track(
        self,
        track: Track,
        destination: Path,
        progress: Callable[[int, int | None], None] | None = None,
    ) -> int:
        """Stream a song into a unique temporary file, then move it into place."""
        source_url = _checked_page_url(track.url)
        if not urlparse(source_url).path.startswith("/download/"):
            raise ValueError("Expected a song download link from an album page.")
        request = Request(source_url, headers={"User-Agent": USER_AGENT})
        try:
            response = urlopen(request, timeout=60)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"Could not download {track.title}: {exc}") from exc

        temporary_path: Path | None = None
        try:
            with response:
                content_type = response.headers.get_content_type()
                if not content_type.startswith("audio/"):
                    raise RuntimeError(
                        f"Expected audio for {track.title}, received {content_type}."
                    )
                raw_length = response.headers.get("Content-Length")
                try:
                    total = int(raw_length) if raw_length else None
                except ValueError:
                    total = None
                destination.parent.mkdir(parents=True, exist_ok=True)
                size = 0
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    prefix=f".{destination.name}.",
                    suffix=".part",
                    dir=destination.parent,
                    delete=False,
                ) as output:
                    temporary_path = Path(output.name)
                    while chunk := response.read(128 * 1024):
                        output.write(chunk)
                        size += len(chunk)
                        if progress:
                            progress(size, total)
            temporary_path.replace(destination)
            return size
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise
