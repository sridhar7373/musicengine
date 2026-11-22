"""Flask HTTP API backed by the shared music-engine service layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request

from .service import (
    DownloadPlan,
    DownloadResult,
    TrackFailure,
    build_download_plan,
    enrich_file,
    execute_download,
)


def _download_options(payload: dict[str, Any]) -> tuple[str, Path, Any, float, bool]:
    artist = payload.get("artist")
    if not isinstance(artist, str) or not artist.strip():
        raise ValueError("'artist' must be a non-empty string")

    albums = payload.get("albums")
    if albums is not None:
        if isinstance(albums, str):
            pass
        elif isinstance(albums, list) and all(isinstance(item, str) for item in albums):
            pass
        else:
            raise ValueError("'albums' must be a string or a list of strings")

    output = payload.get("output", str(Path.home() / "Music"))
    if not isinstance(output, str) or not output.strip():
        raise ValueError("'output' must be a non-empty path string")

    delay = payload.get("delay", 1.0)
    if isinstance(delay, bool) or not isinstance(delay, (int, float)) or delay < 0:
        raise ValueError("'delay' must be a non-negative number")

    no_metadata = payload.get("no_metadata", False)
    if not isinstance(no_metadata, bool):
        raise ValueError("'no_metadata' must be a boolean")
    return artist.strip(), Path(output).expanduser(), albums, float(delay), no_metadata


def _plan_json(plan: DownloadPlan) -> dict[str, Any]:
    return {
        "artist": plan.artist,
        "provider": plan.provider_name,
        "output": str(plan.output),
        "albums": [album.title for album in plan.albums],
        "tracks": [
            {"album": track.album, "title": track.title} for track in plan.tracks
        ],
        "new_tracks": len(plan.new_tracks),
        "refresh_tracks": len(plan.refresh_tracks),
        "up_to_date": plan.up_to_date,
    }


def _failure_json(failure: TrackFailure) -> dict[str, str]:
    return {
        "album": failure.track.album,
        "title": failure.track.title,
        "error": failure.message,
    }


def _result_json(plan: DownloadPlan, result: DownloadResult) -> dict[str, Any]:
    return {
        "plan": _plan_json(plan),
        "result": {
            "downloaded": result.downloaded,
            "refreshed": result.refreshed,
            "up_to_date": result.up_to_date,
            "tagged": result.tagged,
            "covers": result.covers,
            "metadata_skipped": result.metadata_skipped,
            "failures": [_failure_json(item) for item in result.failures],
            "metadata_failures": [
                _failure_json(item) for item in result.metadata_failures
            ],
        },
    }


def create_app() -> Flask:
    """Create the HTTP application; routes call the same service as the CLI."""
    app = Flask(__name__)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/api/downloads/plan")
    def plan_download():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Send a JSON object in the request body"}), 400
        try:
            artist, output, albums, delay, no_metadata = _download_options(payload)
            plan = build_download_plan(
                artist,
                output=output,
                albums=albums,
                delay=delay,
                no_metadata=no_metadata,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 502
        except OSError as exc:
            return jsonify({"error": str(exc)}), 500
        return jsonify(_plan_json(plan))

    @app.post("/api/downloads")
    def download():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Send a JSON object in the request body"}), 400
        try:
            artist, output, albums, delay, no_metadata = _download_options(payload)
            plan = build_download_plan(
                artist,
                output=output,
                albums=albums,
                delay=delay,
                no_metadata=no_metadata,
            )
            result = execute_download(plan, delay=delay)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 502
        except OSError as exc:
            return jsonify({"error": str(exc)}), 500
        return jsonify(_result_json(plan, result))

    @app.post("/api/enrich")
    def enrich():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Send a JSON object in the request body"}), 400
        path = payload.get("path")
        if not isinstance(path, str) or not path.strip():
            return jsonify({"error": "'path' must be a non-empty string"}), 400
        mp3_path = Path(path).expanduser()
        if not mp3_path.is_file():
            return jsonify({"error": f"MP3 file not found: {mp3_path}"}), 404
        delay = payload.get("delay", 1.0)
        if isinstance(delay, bool) or not isinstance(delay, (int, float)) or delay < 0:
            return jsonify({"error": "'delay' must be a non-negative number"}), 400
        for field in ("title", "album", "artist"):
            if payload.get(field) is not None and not isinstance(payload[field], str):
                return jsonify({"error": f"'{field}' must be a string"}), 400
        try:
            metadata, cover_added = enrich_file(
                mp3_path,
                payload.get("title"),
                payload.get("album"),
                payload.get("artist"),
                delay=float(delay),
            )
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 502
        except OSError as exc:
            return jsonify({"error": str(exc)}), 500
        return jsonify(
            {
                "title": metadata.title,
                "performers": metadata.performers,
                "album": metadata.album,
                "album_artist": metadata.album_artist,
                "date": metadata.date,
                "track_number": metadata.track_number,
                "track_count": metadata.track_count,
                "metadata_source": metadata.source,
                "cover_added": cover_added,
            }
        )

    return app


__all__ = ["create_app"]
