"""Command line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

from .console import Console
from .library import track_path
from .providers import provider_for_artist_input
from .providers.base import Album, Track
from .settings import load_default_artist, save_default_artist
from .tagging import enrich_mp3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="music-engine",
        description="Preview or download songs from a supported provider.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download", help="Download an artist discography")
    download.add_argument(
        "artist", nargs="?", help="Artist name or direct page URL (uses saved default if omitted)"
    )
    download.add_argument("-o", "--output", type=Path, default=Path("Music"))
    download.add_argument(
        "--album", action="append", help="Only include matching albums; repeatable"
    )
    download.add_argument("--dry-run", action="store_true", help="Preview without downloading")
    download.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    download.add_argument(
        "--delay", type=float, default=1.0, help="Pause between requests in seconds (default: 1)"
    )
    download.add_argument("--verbose", action="store_true", help="Show albums and tracks")
    download.add_argument("--no-color", action="store_true", help="Disable terminal colors")
    download.add_argument(
        "--no-metadata", action="store_true", help="Skip catalog tag and cover lookup"
    )

    set_artist = commands.add_parser("set-artist", help="Save the default artist for downloads")
    set_artist.add_argument("artist", help="Artist name or direct page URL")
    set_artist.add_argument("--no-color", action="store_true", help="Disable terminal colors")

    enrich = commands.add_parser("enrich", help="Replace MP3 tags and site cover art")
    enrich.add_argument("path", type=Path, help="MP3 file to update")
    enrich.add_argument("--title", help="Override the title inferred from the filename")
    enrich.add_argument("--album", help="Override the album inferred from its folder")
    enrich.add_argument("--artist", help="Override the artist inferred from its folder")
    enrich.add_argument(
        "--delay", type=float, default=1.0, help="Pause between catalog requests in seconds"
    )
    enrich.add_argument("--no-color", action="store_true", help="Disable terminal colors")
    return parser


def _matches(album: Album, filters: list[str] | None) -> bool:
    if not filters:
        return True
    return any(term.casefold() in album.title.casefold() for term in filters)


def _confirm(count: int, root: Path, console: Console) -> bool:
    prompt = console.paint("Download", "cyan", "bold")
    try:
        answer = input(f"{prompt} {count} tracks to {root.resolve()}? [y/N] ")
    except EOFError:
        return False
    return answer.strip().casefold() in {"y", "yes"}


def _track_destination(output: Path, artist: str, track: Track) -> Path:
    return track_path(output, artist, track.album, track.title)


def run_download(args: argparse.Namespace, console: Console) -> int:
    if args.delay < 0:
        console.error("--delay must be zero or greater.")
        return 2

    artist_input = args.artist or load_default_artist()
    if not artist_input:
        console.error('Provide an artist or set one with: music-engine set-artist "Vijay Antony"')
        return 2
    provider, artist_url = provider_for_artist_input(artist_input, delay=args.delay)
    artist, albums = provider.artist_albums(artist_url, delay=args.delay)
    albums = [album for album in albums if _matches(album, args.album)]
    if not albums:
        console.error("No matching albums found.")
        return 1

    tracks: list[Track] = []
    for index, album in enumerate(albums, start=1):
        if args.verbose:
            console.line(f"Reading {album.title}")
        else:
            console.progress("Scanning", index, len(albums))
        tracks.extend(provider.album_tracks(album, delay=args.delay))
    console.end_progress()
    if not tracks:
        console.error("No downloadable tracks found.")
        return 1

    console.line(
        f"{console.paint(provider.name, 'cyan', 'bold')} "
        f"{console.paint('·', 'dim')} {console.paint(artist, 'bold')}"
    )
    skipped = 0
    pending: list[Track] = []
    for track in tracks:
        destination = _track_destination(args.output, artist, track)
        if destination.exists():
            skipped += 1
        else:
            pending.append(track)

    console.line(
        f"{len(albums)} albums {console.paint('·', 'dim')} "
        f"{len(tracks)} tracks {console.paint('·', 'dim')} "
        f"{skipped} already present"
    )
    if args.verbose:
        for track in tracks:
            marker = "✓" if _track_destination(args.output, artist, track).exists() else "·"
            console.line(f"  {marker} {track.album} / {track.title}")

    if args.dry_run:
        console.line(console.paint("Preview only · no files downloaded", "yellow"))
        return 0
    if not pending:
        console.line(console.paint("Library is up to date", "green"))
        return 0
    if not args.yes and not _confirm(len(pending), args.output, console):
        console.line(console.paint("Cancelled", "yellow"))
        return 0

    downloaded = 0
    tagged = 0
    covers = 0
    metadata_skipped = 0
    failures = 0
    for index, track in enumerate(pending, start=1):
        destination = _track_destination(args.output, artist, track)
        try:
            provider.download_track(track, destination)
            downloaded += 1
            if not args.no_metadata:
                try:
                    _, cover_added = enrich_mp3(
                        destination, track.title, track.album, artist, delay=args.delay
                    )
                    tagged += 1
                    covers += int(cover_added)
                except Exception as exc:
                    metadata_skipped += 1
                    if args.verbose:
                        console.error(f"Metadata skipped for {track.title}: {exc}")
        except (OSError, RuntimeError, ValueError) as exc:
            failures += 1
            console.error(f"{track.album} / {track.title}: {exc}")
        console.progress("Downloading", index, len(pending))
        if args.delay and index < len(pending):
            time.sleep(args.delay)
    console.end_progress()

    result = [f"{console.paint(str(downloaded), 'green')} downloaded", f"{skipped} skipped"]
    if not args.no_metadata:
        result.extend((f"{tagged} tagged", f"{covers} covers", f"{metadata_skipped} metadata skipped"))
    result.append(
        f"{console.paint(str(failures), 'red' if failures else 'green')} failed"
    )
    console.line(f" {console.paint('·', 'dim')} ".join(result))
    return 1 if failures else 0


def run_enrich(args: argparse.Namespace, console: Console) -> int:
    if args.delay < 0:
        console.error("--delay must be zero or greater.")
        return 2
    path = args.path.expanduser()
    title = args.title or path.stem
    album = args.album or path.parent.name
    artist = args.artist or path.parent.parent.name
    metadata, cover_added = enrich_mp3(path, title, album, artist, delay=args.delay)
    cover_message = (
        "cover from Cover Art Archive"
        if cover_added
        else "site art removed; no catalog cover found"
    )
    console.line(
        f"{console.paint('Updated', 'green', 'bold')} {metadata.title} "
        f"{console.paint('·', 'dim')} {metadata.album} "
        f"{console.paint('·', 'dim')} tags from {metadata.source} "
        f"{console.paint('·', 'dim')} {cover_message}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    console = Console(no_color=args.no_color)
    try:
        if args.command == "set-artist":
            save_default_artist(args.artist)
            console.line(
                f"{console.paint('✓', 'green')} Default artist set to "
                f"{console.paint(args.artist.strip(), 'bold')}"
            )
            return 0
        if args.command == "enrich":
            return run_enrich(args, console)
        return run_download(args, console)
    except (OSError, RuntimeError, ValueError) as exc:
        console.error(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
