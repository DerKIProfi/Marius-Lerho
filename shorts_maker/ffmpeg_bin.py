"""Resolve ffmpeg/ffprobe binaries without requiring Homebrew."""

from __future__ import annotations

import os
import shutil
from functools import lru_cache
from pathlib import Path


class FFmpegNotFoundError(RuntimeError):
    pass


def _candidate_bins(name: str) -> list[Path]:
    paths: list[Path] = []
    which = shutil.which(name)
    if which:
        paths.append(Path(which))

    # Common macOS / Linux locations (Homebrew Intel + Apple Silicon, MacPorts, …)
    for base in (
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/opt/local/bin",
        "/usr/bin",
        str(Path.home() / "bin"),
        str(Path.home() / ".local" / "bin"),
    ):
        paths.append(Path(base) / name)

    env = os.environ.get("FFMPEG_BINARY" if name == "ffmpeg" else "FFPROBE_BINARY")
    if env:
        paths.insert(0, Path(env))

    # Bundled static binary via imageio-ffmpeg (no brew needed)
    if name == "ffmpeg":
        try:
            import imageio_ffmpeg

            paths.insert(0, Path(imageio_ffmpeg.get_ffmpeg_exe()))
        except Exception:
            pass

    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


@lru_cache(maxsize=1)
def ffmpeg_path() -> str:
    for path in _candidate_bins("ffmpeg"):
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())
    raise FFmpegNotFoundError(
        "ffmpeg nicht gefunden.\n"
        "Ohne Homebrew reicht:\n"
        "  python3 -m pip install imageio-ffmpeg\n"
        "Oder Homebrew installieren und dann: brew install ffmpeg\n"
        "Siehe ANLEITUNG_MARIUS.md Abschnitt „ffmpeg ohne brew“."
    )


@lru_cache(maxsize=1)
def ffprobe_path() -> str | None:
    for path in _candidate_bins("ffprobe"):
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())
    try:
        sibling = Path(ffmpeg_path()).with_name("ffprobe")
    except FFmpegNotFoundError:
        return None
    if sibling.is_file() and os.access(sibling, os.X_OK):
        return str(sibling.resolve())
    return None


def ffmpeg_dir_for_ytdlp() -> str:
    """Directory containing ffmpeg — yt-dlp's ffmpeg_location option."""
    return str(Path(ffmpeg_path()).parent)
