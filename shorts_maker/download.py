"""Download YouTube (or other) videos via yt-dlp, or accept a local file path."""

from __future__ import annotations

import re
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

# Prefer progressive single-file formats first so ffmpeg does not need to merge
# separate video+audio streams (often fails on Homebrew / macOS ffmpeg builds).
_FORMAT_CANDIDATES: tuple[dict, ...] = (
    {
        # Progressive MP4 only (no merge)
        "format": "b[ext=mp4]/best[ext=mp4]/b",
        "merge_output_format": None,
    },
    {
        # Any progressive single file (webm/mkv ok)
        "format": "b",
        "merge_output_format": None,
    },
    {
        # Classic YouTube progressive itags when still available
        "format": "22/18/mp4",
        "merge_output_format": None,
    },
    {
        # Separate streams → merge to mp4 (last resort)
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
        "merge_output_format": "mp4",
    },
    {
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
    },
)

_VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}


def download_video(url_or_path: str, out_dir: Path) -> Path:
    """
    If *url_or_path* is an existing local file, return it.
    Otherwise download with yt-dlp into *out_dir* and return the path.
    """
    path = Path(url_or_path).expanduser()
    if path.is_file():
        return path.resolve()

    out_dir.mkdir(parents=True, exist_ok=True)
    url = url_or_path

    # Reuse an existing download for this URL (avoids re-merge failures).
    existing = find_existing_download(url, out_dir)
    if existing is not None:
        return existing

    last_error: Exception | None = None
    for candidate in _FORMAT_CANDIDATES:
        ydl_opts: dict = {
            "format": candidate["format"],
            "outtmpl": str(out_dir / "%(title).80B [%(id)s].%(ext)s"),
            "noplaylist": True,
            "quiet": False,
            "no_warnings": False,
        }
        merge_fmt = candidate.get("merge_output_format")
        if merge_fmt:
            ydl_opts["merge_output_format"] = merge_fmt

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = Path(ydl.prepare_filename(info))
                if filename.exists():
                    return filename.resolve()
                found = _find_by_id(out_dir, str(info.get("id") or ""))
                if found is not None:
                    return found
                raise FileNotFoundError(f"Download finished but file missing: {filename}")
        except DownloadError as exc:
            last_error = exc
            msg = str(exc).lower()
            if any(k in msg for k in ("conversion failed", "postprocessing", "ffmpeg", "merging")):
                continue
            raise

    assert last_error is not None
    raise last_error


def find_existing_download(url: str, out_dir: Path) -> Path | None:
    """Return a previously downloaded file for this video id, if present."""
    video_id = extract_youtube_id(url)
    if not video_id or not out_dir.exists():
        return None
    return _find_by_id(out_dir, video_id)


def extract_youtube_id(url: str) -> str | None:
    patterns = (
        r"(?:v=|/shorts/|youtu\.be/)([A-Za-z0-9_-]{6,})",
        r"youtube\.com/watch\?.*?v=([A-Za-z0-9_-]{6,})",
    )
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def _find_by_id(out_dir: Path, video_id: str) -> Path | None:
    if not video_id or not out_dir.exists():
        return None
    matches = [
        p
        for p in out_dir.iterdir()
        if p.is_file() and video_id in p.name and p.suffix.lower() in _VIDEO_EXTS
    ]
    if not matches:
        return None
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0].resolve()
