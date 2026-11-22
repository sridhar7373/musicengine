"""Apply catalog metadata and front artwork to MP3 ID3 tags."""

from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

from mutagen.id3 import APIC, ID3, TALB, TCON, TDRC, TIT2, TPE1, TPE2, TPOS, TRCK
from mutagen.mp3 import MP3

from .metadata import TrackMetadata


def _remove_id3v1(path: Path) -> None:
    size = path.stat().st_size
    if size < 128:
        return
    with path.open("r+b") as audio_file:
        audio_file.seek(-128, 2)
        if audio_file.read(3) == b"TAG":
            audio_file.truncate(size - 128)


def _remove_site_frames(tags) -> None:
    for key, frame in list(tags.items()):
        if "isaimini" in key.casefold() or "isaimini" in repr(frame).casefold():
            del tags[key]


def update_mp3(path: Path, metadata: TrackMetadata, cover: tuple[bytes, str] | None) -> bool:
    """Atomically replace site tags/artwork; return whether a new cover was added."""
    if path.suffix.casefold() != ".mp3" or not path.is_file():
        raise ValueError(f"Not an MP3 file: {path}")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        shutil.copy2(path, temporary_path)
        _remove_id3v1(temporary_path)

        audio = MP3(temporary_path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        tags = audio.tags
        for frame in (
            "TIT2", "TPE1", "TALB", "TPE2", "TDRC", "TRCK", "TPOS", "TCON",
            "APIC", "COMM", "TXXX", "WXXX", "WCOM", "WOAR", "TCOP", "TPUB", "TENC",
        ):
            tags.delall(frame)
        _remove_site_frames(tags)

        tags.add(TIT2(encoding=3, text=[metadata.title]))
        tags.add(TPE1(encoding=3, text=[metadata.performers]))
        tags.add(TALB(encoding=3, text=[metadata.album]))
        tags.add(TPE2(encoding=3, text=[metadata.album_artist]))
        if metadata.date:
            tags.add(TDRC(encoding=3, text=[metadata.date[:10]]))
        if metadata.track_number:
            count = f"/{metadata.track_count}" if metadata.track_count else ""
            tags.add(TRCK(encoding=3, text=[f"{metadata.track_number}{count}"]))
        if metadata.disc_number:
            tags.add(TPOS(encoding=3, text=[str(metadata.disc_number)]))
        if metadata.genre:
            tags.add(TCON(encoding=3, text=[metadata.genre]))
        if cover:
            image_data, mime = cover
            tags.add(APIC(encoding=3, mime=mime, type=3, desc="Front cover", data=image_data))

        audio.save(v2_version=3)
        temporary_path.replace(path)
        return cover is not None
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def enrich_mp3(
    path: Path,
    title: str,
    album: str,
    artist: str,
    delay: float = 1.0,
) -> tuple[TrackMetadata, bool]:
    """Resolve metadata through the catalog waterfall, then update the MP3."""
    from .metadata import find_track_metadata, get_cover_art

    metadata = find_track_metadata(title, album, artist, delay=delay)
    if delay:
        import time

        time.sleep(delay)
    cover = get_cover_art(metadata, delay=delay)
    cover_added = update_mp3(path, metadata, cover)
    return metadata, cover_added
