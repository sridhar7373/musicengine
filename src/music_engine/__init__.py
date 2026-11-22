"""Shared music service API and command-line tools."""

from .service import (
    DownloadPlan,
    DownloadResult,
    TrackFailure,
    build_download_plan,
    destination_for_track,
    enrich_file,
    execute_download,
)

__version__ = "0.1.0"

__all__ = [
    "DownloadPlan",
    "DownloadResult",
    "TrackFailure",
    "build_download_plan",
    "destination_for_track",
    "enrich_file",
    "execute_download",
]
