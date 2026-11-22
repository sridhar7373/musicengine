# Music Engine

A small CLI and local HTTP API that collect albums from a supported provider's artist discography page, preview tracks, and download them into an artist/album folder structure. Isaimini is the first provider. Use it only for music you own or are authorized to download.

## Install

Requires Python 3.10 or newer. From the project directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

This installs the CLI and Flask dependency.

## Download an artist discography

Save the artist once:

```sh
music-engine set-artist "Vijay Antony"
```

This default is stored in `${XDG_CONFIG_HOME:-~/.config}/music-engine/config.json`.

Then omit the artist on later commands:

```sh
music-engine download --album Vedi --album Dishyum --output ~/Music
```

You can still pass an artist name or direct artist page URL to override the saved default:

```sh
music-engine download "Vijay Antony" --output ~/Music
```

The default provider resolves the artist name from its directory. The CLI shows a compact colored summary and per-track download progress with transfer speed, then asks before downloading. To preview without downloading:

```sh
music-engine download "Vijay Antony" --output ~/Music --dry-run
```

Every new download is enriched automatically: the CLI looks up ID3 tags with iTunes first and MusicBrainz as a fallback. It uses artwork from the matched iTunes result first, then falls back to the MusicBrainz Cover Art Archive. To update an MP3 that was already downloaded:

```sh
music-engine enrich "~/Music/Vijay Antony/Vedi/Bombay Ponnu.mp3"
```

When you rerun `download`, existing tracks with Isaimini branding are queued for metadata refresh; clean tracks are skipped. The `enrich` command is still available for updating one MP3 directly. It infers title, album, and artist from the filename and folders. Pass `--title`, `--album`, or `--artist` to override them. Use `--no-metadata` with `download` to skip enrichment and refreshes.

To restrict the download to matching album names, repeat `--album` as needed:

```sh
music-engine download "Vijay Antony" --album Vedi --album Dishyum --output ~/Music
```

Use `--yes` to skip the confirmation prompt. Clean existing tracks are skipped; branded tracks are refreshed. Files are organized as `Artist/Album/Track.mp3` under the output directory. Requests are spaced by one second by default; increase this with `--delay 2` if needed. Add `--verbose` to list albums and tracks, or `--no-color` to disable colors.

## Flask HTTP API

Start the local Flask API. It binds to localhost by default:

```sh
music-engine serve
```

Preview a download plan without changing files:

```sh
curl -X POST http://127.0.0.1:5000/api/downloads/plan \
  -H 'Content-Type: application/json' \
  -d '{"artist":"Vijay Antony","albums":["Vedi"]}'
```

Run downloads and metadata refreshes:

```sh
curl -X POST http://127.0.0.1:5000/api/downloads \
  -H 'Content-Type: application/json' \
  -d '{"artist":"Vijay Antony","albums":["Vedi"],"delay":1.0}'
```

The API also provides `GET /api/health` and `POST /api/enrich`:

```sh
curl -X POST http://127.0.0.1:5000/api/enrich \
  -H 'Content-Type: application/json' \
  -d "{\"path\":\"$HOME/Music/Vijay Antony/Vedi/Bombay Ponnu.mp3\"}"
```

Downloads run synchronously and return a JSON summary when complete. Flask routes and the CLI use the same workflow in `src/music_engine/service.py`.

## Python service API

Python callers can use the shared service directly:

```python
from pathlib import Path
from music_engine import build_download_plan, execute_download

plan = build_download_plan(
    "Vijay Antony",
    output=Path.home() / "Music",
    albums=["Vedi"],
    delay=1.0,
)
print(f"{len(plan.new_tracks)} new; {len(plan.refresh_tracks)} need metadata refresh")

result = execute_download(plan, delay=1.0)
print(f"Downloaded {result.downloaded}; refreshed {result.refreshed}")
```

`build_download_plan` only reads the catalog and filesystem. Files are changed only when `execute_download` is called. Use `enrich_file(path, title=..., album=..., artist=...)` to enrich one MP3 programmatically.

## Provider code

Provider implementations live in `src/music_engine/providers/`:

- `base.py` defines the shared provider interface and album/track records.
- `isaimini.py` implements the Isaimini directory lookup and downloads.
- `__init__.py` selects a provider for a URL and defines the default provider for artist names.

To add a provider, implement `BaseProvider` in this folder and register it in `PROVIDER_TYPES` in `__init__.py`.

Metadata sources live in `src/music_engine/metadata/`:

- `base.py` defines the `MetadataProvider` and `ArtworkProvider` base classes.
- `itunes.py` and `musicbrainz.py` provide track metadata.
- `cover_art_archive.py` provides front-cover lookup.
- `__init__.py` sets the waterfall order in `METADATA_PROVIDERS` and `ARTWORK_PROVIDERS`.

Add a source as its own module, subclass the relevant base class, and register it in `__init__.py`.
