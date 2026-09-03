from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from yt_dlp import YoutubeDL


SAFE_NAME = re.compile(r"[^\w\-]+", re.UNICODE)


def _sanitize(name: str, max_len: int = 80) -> str:
    cleaned = SAFE_NAME.sub("_", name.strip()).strip("_")
    return (cleaned or "video")[:max_len]


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def download_video(url: str, output_dir: Path, *, max_height: int = 1080) -> Path:
    """Lädt ein YouTube-Video herunter und gibt den lokalen Pfad zurück."""
    output_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(output_dir / "%(id)s.%(ext)s")

    opts = {
        "format": f"bv*[height<={max_height}]+ba/b[height<={max_height}]/b",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "writesubtitles": False,
        "writeinfojson": True,
    }

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info["id"]
        title = _sanitize(info.get("title") or video_id)

    # yt-dlp may produce mp4 after merge
    candidates = list(output_dir.glob(f"{video_id}.*"))
    media = [p for p in candidates if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}]
    if not media:
        raise FileNotFoundError(f"Kein Video nach Download gefunden für {video_id}")

    source = max(media, key=lambda p: p.stat().st_size)
    target = output_dir / f"{title}_{video_id}{source.suffix}"
    if source != target:
        source.replace(target)
    return target
