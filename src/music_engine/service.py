"""Shared catalog, download, and enrichment workflows for CLI and HTTP API."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import time
from typing import Callable

from .library import track_path
from .metadata.common import TrackMetadata
from .providers import provider_for_artist_input
from .providers.base import Album, BaseProvider, Track
from .tagging import enrich_mp3, has_site_branding


@dataclass(frozen=True)
class DownloadPlan:
    """Tracks that are new, branded, or already current in a music library."""

    artist: str
    provider_name: str
    output: Path
    albums: tuple[Album, ...]
    tracks: tuple[Track, ...]
    new_tracks: tuple[Track, ...]
    refresh_tracks: tuple[Track, ...]
    up_to_date: int
    metadata_enabled: bool
    _provider: BaseProvider = field(repr=False, compare=False)


@dataclass(frozen=True)
class TrackFailure:
    track: Track
    message: str


@dataclass(frozen=True)
class DownloadResult:
    downloaded: int = 0
    refreshed: int = 0
    up_to_date: int = 0
    tagged: int = 0
    covers: int = 0
    metadata_skipped: int = 0
    failures: tuple[TrackFailure, ...] = ()
    metadata_failures: tuple[TrackFailure, ...] = ()


AlbumProgress = Callable[[Album, int, int], None]
TrackStart = Callable[[Track, int, int], None]
TrackProgress = Callable[[Track, int, int, int, int | None], None]
TrackComplete = Callable[[Track, int, int, int], None]
RefreshComplete = Callable[[Track, int, int], None]


def _matches_album(album: Album, filters: tuple[str, ...] | None) -> bool:
    if not filters:
        return True
    return any(term.casefold() in album.title.casefold() for term in filters)


def destination_for_track(plan: DownloadPlan, track: Track) -> Path:
    """Return the path where the plan stores a track."""
    return track_path(plan.output, plan.artist, track.album, track.title)


def build_download_plan(
    artist: str,
    output: Path = Path("Music"),
    albums: str | tuple[str, ...] | list[str] | None = None,
    delay: float = 1.0,
    no_metadata: bool = False,
    on_album: AlbumProgress | None = None,
) -> DownloadPlan:
    """Resolve an artist catalog and classify tracks without changing files."""
    if delay < 0:
        raise ValueError("delay must be zero or greater")
    if not artist or not artist.strip():
        raise ValueError("artist must be a name or supported artist page URL")

    provider, artist_url = provider_for_artist_input(artist.strip(), delay=delay)
    artist_name, catalog_albums = provider.artist_albums(artist_url, delay=delay)
    album_filters = (
        (albums,) if isinstance(albums, str) else tuple(albums) if albums else None
    )
    selected_albums = tuple(
        album for album in catalog_albums if _matches_album(album, album_filters)
    )
    if not selected_albums:
        raise ValueError("No matching albums found.")

    tracks: list[Track] = []
    for index, album in enumerate(selected_albums, start=1):
        if on_album:
            on_album(album, index, len(selected_albums))
        tracks.extend(provider.album_tracks(album, delay=delay))
    if not tracks:
        raise ValueError("No downloadable tracks found.")

    output_path = Path(output).expanduser()
    new_tracks = []
    refresh_tracks = []
    up_to_date = 0
    for track in tracks:
        destination = track_path(output_path, artist_name, track.album, track.title)
        if not destination.exists():
            new_tracks.append(track)
        elif not no_metadata and has_site_branding(destination):
            refresh_tracks.append(track)
        else:
            up_to_date += 1

    return DownloadPlan(
        artist=artist_name,
        provider_name=provider.name,
        output=output_path,
        albums=selected_albums,
        tracks=tuple(tracks),
        new_tracks=tuple(new_tracks),
        refresh_tracks=tuple(refresh_tracks),
        up_to_date=up_to_date,
        metadata_enabled=not no_metadata,
        _provider=provider,
    )


def execute_download(
    plan: DownloadPlan,
    delay: float = 1.0,
    on_track_start: TrackStart | None = None,
    on_progress: TrackProgress | None = None,
    on_track_complete: TrackComplete | None = None,
    on_refresh_complete: RefreshComplete | None = None,
) -> DownloadResult:
    """Execute a plan, report per-track progress, and return a summary."""
    if delay < 0:
        raise ValueError("delay must be zero or greater")

    downloaded = refreshed = tagged = covers = metadata_skipped = 0
    failures: list[TrackFailure] = []
    metadata_failures: list[TrackFailure] = []
    action_count = len(plan.new_tracks) + len(plan.refresh_tracks)
    action_index = 0

    for index, track in enumerate(plan.new_tracks, start=1):
        action_index += 1
        destination = destination_for_track(plan, track)
        if on_track_start:
            on_track_start(track, index, len(plan.new_tracks))
        try:
            size = plan._provider.download_track(
                track,
                destination,
                progress=(
                    (lambda received, total, t=track, i=index: on_progress(
                        t, i, len(plan.new_tracks), received, total
                    ))
                    if on_progress
                    else None
                ),
            )
            downloaded += 1
            if on_track_complete:
                on_track_complete(track, index, len(plan.new_tracks), size)
            if plan.metadata_enabled:
                try:
                    _, cover_added = enrich_mp3(
                        destination, track.title, track.album, plan.artist, delay=delay
                    )
                    tagged += 1
                    covers += int(cover_added)
                except Exception as exc:
                    metadata_skipped += 1
                    metadata_failures.append(TrackFailure(track, str(exc)))
        except (OSError, RuntimeError, ValueError) as exc:
            failures.append(TrackFailure(track, str(exc)))
        if delay and action_index < action_count:
            time.sleep(delay)

    for index, track in enumerate(plan.refresh_tracks, start=1):
        action_index += 1
        destination = destination_for_track(plan, track)
        try:
            _, cover_added = enrich_mp3(
                destination, track.title, track.album, plan.artist, delay=delay
            )
            tagged += 1
            refreshed += 1
            covers += int(cover_added)
            if on_refresh_complete:
                on_refresh_complete(track, index, len(plan.refresh_tracks))
        except Exception as exc:
            metadata_skipped += 1
            metadata_failures.append(TrackFailure(track, str(exc)))
        if delay and action_index < action_count:
            time.sleep(delay)

    return DownloadResult(
        downloaded=downloaded,
        refreshed=refreshed,
        up_to_date=plan.up_to_date,
        tagged=tagged,
        covers=covers,
        metadata_skipped=metadata_skipped,
        failures=tuple(failures),
        metadata_failures=tuple(metadata_failures),
    )


def enrich_file(
    path: Path,
    title: str | None = None,
    album: str | None = None,
    artist: str | None = None,
    delay: float = 1.0,
) -> tuple[TrackMetadata, bool]:
    """Enrich one MP3; infer missing tags from its filename and folders."""
    path = Path(path).expanduser()
    if delay < 0:
        raise ValueError("delay must be zero or greater")
    resolved_title = title or path.stem
    resolved_album = album or path.parent.name
    resolved_artist = artist or path.parent.parent.name
    return enrich_mp3(
        path, resolved_title, resolved_album, resolved_artist, delay=delay
    )


__all__ = [
    "DownloadPlan",
    "DownloadResult",
    "TrackFailure",
    "build_download_plan",
    "destination_for_track",
    "enrich_file",
    "execute_download",
]
