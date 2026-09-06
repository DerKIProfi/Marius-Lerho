"""Download YouTube (or other) videos via yt-dlp, or accept a local file path."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

# Progressive / remux-friendly first. Never start with the default bv*+ba→mp4
# merge — that is what fails on many macOS Homebrew ffmpeg builds.
_FORMAT_CANDIDATES: tuple[dict, ...] = (
    {
        "label": "progressive≤720p",
        "format": (
            "best[height<=720][acodec!=none][vcodec!=none][ext=mp4]/"
            "best[height<=720][acodec!=none][vcodec!=none]/"
            "best[acodec!=none][vcodec!=none][ext=mp4]/"
            "best[acodec!=none][vcodec!=none]"
        ),
        "merge_output_format": None,
    },
    {
        "label": "itag-18/22",
        "format": "18/22",
        "merge_output_format": None,
    },
    {
        "label": "avc1+mp4a→mp4",
        "format": (
            "bv*[vcodec^=avc1][height<=720]+ba[acodec^=mp4a]/"
            "bv*[vcodec^=avc1]+ba[acodec^=mp4a]/"
            "b[ext=mp4]"
        ),
        "merge_output_format": "mp4",
    },
    {
        "label": "any→mkv",
        "format": "bv*[height<=720]+ba/bv*+ba/b",
        "merge_output_format": "mkv",
    },
)

_VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}
_MIN_COMPLETE_BYTES = 1_000_000
# yt-dlp leftovers: VIDEOID.f303.webm, VIDEOID.temp.mp4, *.part, …
_PARTIAL_NAME = re.compile(
    r"(?:\.f\d+\.)|(?:\.temp\.)|(?:\.part$)|(?:\.ytdl$)|(?:\.temp$)",
    re.IGNORECASE,
)


def download_video(url_or_path: str, out_dir: Path, *, max_height: int = 720) -> Path:
    """
    If *url_or_path* is an existing local file, return it.
    Otherwise download with yt-dlp into *out_dir* and return the path.
    """
    path = Path(url_or_path).expanduser()
    if path.is_file():
        return path.resolve()

    out_dir.mkdir(parents=True, exist_ok=True)
    url = url_or_path

    freed = _cleanup_partials(out_dir)
    if freed:
        print(f"  🧹 {freed} partielle Download-Datei(en) gelöscht")

    existing = find_existing_download(url, out_dir)
    if existing is not None:
        print(f"  ↻ Vorhandener Download: {existing.name}")
        return existing

    free = shutil.disk_usage(out_dir).free
    if free < 800_000_000:
        free_gb = free / (1024**3)
        raise OSError(
            f"Zu wenig freier Speicher ({free_gb:.1f} GiB). "
            "Bitte Platz schaffen (z.B. *.f*.webm / *.temp.mp4 in "
            "output/work/download löschen) oder eine lokale MP4 übergeben."
        )

    last_error: Exception | None = None
    for candidate in _FORMAT_CANDIDATES:
        fmt = candidate["format"]
        if max_height != 720:
            fmt = fmt.replace("720", str(max_height))

        print(f"  → Download-Strategie: {candidate['label']}")
        ydl_opts: dict = {
            "format": fmt,
            "outtmpl": str(out_dir / "%(title).80B [%(id)s].%(ext)s"),
            "noplaylist": True,
            "quiet": False,
            "no_warnings": False,
            "retries": 3,
            "fragment_retries": 3,
            "postprocessor_args": {"ffmpeg": ["-c", "copy"]},
        }
        merge_fmt = candidate.get("merge_output_format")
        if merge_fmt:
            ydl_opts["merge_output_format"] = merge_fmt

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = Path(ydl.prepare_filename(info))
                if not filename.exists():
                    alt = filename.with_suffix(f".{merge_fmt}") if merge_fmt else None
                    if alt is not None and alt.exists():
                        filename = alt
                    else:
                        found = _find_by_id(out_dir, str(info.get("id") or ""))
                        if found is None:
                            raise FileNotFoundError(
                                f"Download finished but file missing: {filename}"
                            )
                        filename = found
                return filename.resolve()
        except DownloadError as exc:
            last_error = exc
            msg = str(exc).lower()
            print(f"  ✗ Strategie fehlgeschlagen: {exc}")
            _cleanup_partials(out_dir)
            if "no space left" in msg or "errno 28" in msg:
                raise OSError(
                    "Kein Speicherplatz mehr während des Downloads. "
                    "Partielle Dateien in output/work/download löschen "
                    "oder lokale MP4 nutzen."
                ) from exc
            continue
        except OSError as exc:
            if getattr(exc, "errno", None) == 28 or "no space left" in str(exc).lower():
                raise OSError(
                    "Kein Speicherplatz mehr während des Downloads. "
                    "Partielle Dateien in output/work/download löschen."
                ) from exc
            raise

    assert last_error is not None
    raise last_error


def find_existing_download(url: str, out_dir: Path) -> Path | None:
    """Return a previously downloaded complete file for this video id, if present."""
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


def pick_best_local_video(paths: list[Path]) -> Path:
    """Pick the best complete video among expanded shell globs."""
    files = [p.expanduser() for p in paths if p.expanduser().is_file()]
    complete = [
        p
        for p in files
        if p.suffix.lower() in _VIDEO_EXTS
        and p.stat().st_size >= _MIN_COMPLETE_BYTES
        and not _is_partial_name(p.name)
    ]
    if not complete:
        raise FileNotFoundError(
            "Keine fertige Videodatei gefunden. "
            "Bitte eine konkrete MP4 angeben (nicht die *.f*.webm / *.temp.mp4)."
        )
    # Prefer mp4/mkv, then largest
    complete.sort(
        key=lambda p: (
            0 if p.suffix.lower() in {".mp4", ".mkv"} else 1,
            -p.stat().st_size,
        )
    )
    return complete[0].resolve()


def _is_partial_name(name: str) -> bool:
    return bool(_PARTIAL_NAME.search(name))


def _find_by_id(out_dir: Path, video_id: str) -> Path | None:
    if not video_id or not out_dir.exists():
        return None
    matches = [
        p
        for p in out_dir.iterdir()
        if p.is_file()
        and video_id in p.name
        and p.suffix.lower() in _VIDEO_EXTS
        and p.stat().st_size >= _MIN_COMPLETE_BYTES
        and not _is_partial_name(p.name)
    ]
    if not matches:
        return None
    # Prefer final mp4/mkv containers, then largest (complete > failed temp)
    matches.sort(
        key=lambda p: (
            0 if p.suffix.lower() in {".mp4", ".mkv"} else 1,
            -p.stat().st_size,
        )
    )
    return matches[0].resolve()


def _cleanup_partials(out_dir: Path) -> int:
    """Remove yt-dlp leftovers that waste disk and break reuse. Returns count deleted."""
    if not out_dir.exists():
        return 0
    deleted = 0
    for p in out_dir.iterdir():
        if not p.is_file():
            continue
        if _is_partial_name(p.name):
            try:
                p.unlink()
                deleted += 1
            except OSError:
                pass
    return deleted
