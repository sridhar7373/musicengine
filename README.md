# Music Engine

A small command line tool that collects albums from a supported provider's artist discography page, previews the tracks, and downloads selected songs into an artist/album folder structure. Isaimini is the first provider. Use it only for music you own or are authorized to download.

## Install

Requires Python 3.10 or newer. From the project directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

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

The default provider resolves the artist name from its directory. The CLI shows a compact colored summary and progress bar, then asks before downloading. To preview without downloading:

```sh
music-engine download "Vijay Antony" --output ~/Music --dry-run
```

Every new download is enriched automatically: the CLI looks up ID3 tags with iTunes first and MusicBrainz as a fallback. It uses artwork from the matched iTunes result first, then falls back to the MusicBrainz Cover Art Archive. To update an MP3 that was already downloaded:

```sh
music-engine enrich "~/Music/Vijay Antony/Vedi/Bombay Ponnu.mp3"
```

The enrich command is only needed for files downloaded before automatic enrichment was added. It infers title, album, and artist from the filename and folders. Pass `--title`, `--album`, or `--artist` to override them. Use `--no-metadata` with `download` to skip enrichment.

To restrict the download to matching album names, repeat `--album` as needed:

```sh
music-engine download "Vijay Antony" --album Vedi --album Dishyum --output ~/Music
```

Use `--yes` to skip the confirmation prompt. Existing tracks are skipped. Files are organized as `Artist/Album/Track.mp3` under the output directory. Requests are spaced by one second by default; increase this with `--delay 2` if needed. Add `--verbose` to list albums and tracks, or `--no-color` to disable colors.

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
