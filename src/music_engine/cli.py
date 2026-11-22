"""Command line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from .service import build_download_plan, destination_for_track, enrich_file, execute_download
from .console import Console
from .settings import load_default_artist, save_default_artist


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

    serve = commands.add_parser("serve", help="Run the local Flask HTTP API")
    serve.add_argument("--host", default="127.0.0.1", help="Bind address (default: localhost)")
    serve.add_argument("--port", type=int, default=5000, help="Port (default: 5000)")
    serve.add_argument("--no-color", action="store_true", help="Disable terminal colors")
    return parser


def _confirm(count: int, root: Path, console: Console, refresh_count: int = 0) -> bool:
    prompt = console.paint("Proceed", "cyan", "bold")
    actions = []
    if count:
        actions.append(f"{count} new tracks")
    if refresh_count:
        actions.append(f"refresh metadata on {refresh_count} existing tracks")
    action = " and ".join(actions)
    try:
        answer = input(f"{prompt} {action} to {root.resolve()}? [y/N] ")
    except EOFError:
        return False
    return answer.strip().casefold() in {"y", "yes"}

def run_download(args: argparse.Namespace, console: Console) -> int:
    if args.delay < 0:
        console.error("--delay must be zero or greater.")
        return 2

    artist_input = args.artist or load_default_artist()
    if not artist_input:
        console.error('Provide an artist or set one with: music-engine set-artist "Vijay Antony"')
        return 2
    try:
        plan = build_download_plan(
            artist_input,
            output=args.output,
            albums=args.album,
            delay=args.delay,
            no_metadata=args.no_metadata,
            on_album=(
                (lambda album, _index, _total: console.line(f"Reading {album.title}"))
                if args.verbose
                else lambda _album, index, total: console.progress("Scanning", index, total)
            ),
        )
    except ValueError as exc:
        console.end_progress()
        console.error(str(exc))
        return 1
    console.end_progress()

    console.line(
        f"{console.paint(plan.provider_name, 'cyan', 'bold')} "
        f"{console.paint('·', 'dim')} {console.paint(plan.artist, 'bold')}"
    )

    console.line(
        f"{len(plan.albums)} albums {console.paint('·', 'dim')} "
        f"{len(plan.tracks)} tracks {console.paint('·', 'dim')} "
        f"{len(plan.new_tracks)} new {console.paint('·', 'dim')} "
        f"{len(plan.refresh_tracks)} metadata refresh {console.paint('·', 'dim')} "
        f"{plan.up_to_date} up to date"
    )
    if args.verbose:
        refresh_paths = {
            destination_for_track(plan, track) for track in plan.refresh_tracks
        }
        for track in plan.tracks:
            destination = destination_for_track(plan, track)
            if destination in refresh_paths:
                marker = "↻"
            else:
                marker = "✓" if destination.exists() else "·"
            console.line(f"  {marker} {track.album} / {track.title}")

    if args.dry_run:
        console.line(console.paint("Preview only · no files changed", "yellow"))
        return 0
    if not plan.new_tracks and not plan.refresh_tracks:
        console.line(console.paint("Library is up to date", "green"))
        return 0
    if not args.yes and not _confirm(
        len(plan.new_tracks), plan.output, console, len(plan.refresh_tracks)
    ):
        console.line(console.paint("Cancelled", "yellow"))
        return 0

    download_result = execute_download(
        plan,
        delay=args.delay,
        on_track_start=lambda track, index, total: console.start_download(
            f"Downloading {index:02d}/{total} {track.title}"
        ),
        on_progress=lambda _track, _index, _total, received, expected: console.download_progress(
            received, expected
        ),
        on_track_complete=lambda _track, _index, _total, size: console.finish_download(size),
        on_refresh_complete=(
            (lambda track, index, total: console.line(
                f"  ↻ Refreshed {index}/{total} {track.title}"
            ))
            if args.verbose
            else None
        ),
    )
    console.end_progress()
    for failure in download_result.failures:
        console.error(f"{failure.track.album} / {failure.track.title}: {failure.message}")
    if args.verbose:
        for failure in download_result.metadata_failures:
            console.error(f"Metadata skipped for {failure.track.title}: {failure.message}")

    summary = [
        f"{console.paint(str(download_result.downloaded), 'green')} downloaded",
        f"{download_result.refreshed} refreshed",
        f"{download_result.up_to_date} up to date",
    ]
    if not args.no_metadata:
        summary.extend((
            f"{download_result.tagged} tagged",
            f"{download_result.covers} covers",
            f"{download_result.metadata_skipped} metadata skipped",
        ))
    summary.append(
        f"{console.paint(str(len(download_result.failures)), 'red' if download_result.failures else 'green')} failed"
    )
    console.line(f" {console.paint('·', 'dim')} ".join(summary))
    return 1 if download_result.failures else 0


def run_enrich(args: argparse.Namespace, console: Console) -> int:
    if args.delay < 0:
        console.error("--delay must be zero or greater.")
        return 2
    path = args.path.expanduser()
    metadata, cover_added = enrich_file(
        path, args.title, args.album, args.artist, delay=args.delay
    )
    cover_message = (
        "cover updated from catalog"
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
        if args.command == "serve":
            if not 1 <= args.port <= 65535:
                console.error("--port must be between 1 and 65535.")
                return 2
            from .api import create_app

            create_app().run(host=args.host, port=args.port, debug=False)
            return 0
        return run_download(args, console)
    except (OSError, RuntimeError, ValueError) as exc:
        console.error(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
