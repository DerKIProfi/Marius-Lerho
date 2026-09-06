from __future__ import annotations

import json
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from shorts_maker.captions import chunk_captions, write_ass
from shorts_maker.effects import even_dimensions, plan_zoom_cuts, zoom_expr
from shorts_maker.models import CaptionChunk, EditPlan, Moment, Word


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed:\n"
            + " ".join(cmd)
            + "\n"
            + (result.stderr or result.stdout or "unknown error")
        )


@lru_cache(maxsize=1)
def _ffmpeg_has_ass() -> bool:
    """True, wenn ffmpeg mit libass gebaut wurde (Filter ass/subtitles)."""
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-filters"],
        capture_output=True,
        text=True,
    )
    text = (result.stdout or "") + (result.stderr or "")
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] in {"ass", "subtitles"}:
            return True
    return False


def _find_font() -> Path | None:
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


def _escape_filter_path(path: Path) -> str:
    s = str(path.resolve()).replace("\\", "/")
    return s.replace(":", "\\:").replace("'", "\\'")


def _caption_filter(
    captions: list[CaptionChunk],
    *,
    work_dir: Path,
    width: int,
    height: int,
) -> str:
    """ASS wenn libass da ist, sonst drawtext-Fallback (macOS Homebrew oft ohne libass)."""
    if _ffmpeg_has_ass():
        ass_path = work_dir / "captions.ass"
        write_ass(ass_path, captions, play_res_x=width, play_res_y=height)
        return f"ass=filename='{_escape_filter_path(ass_path)}'"

    font = _find_font()
    font_size = max(36, min(56, int(width * 0.048)))
    y = int(height * 0.72)
    if not captions:
        return "null"

    filters: list[str] = []
    for chunk in captions:
        text = _escape_drawtext(chunk.text.upper())
        start = max(0.0, chunk.start)
        end = max(start + 0.05, chunk.end)
        fontfile = f":fontfile='{_escape_filter_path(font)}'" if font else ""
        filters.append(
            "drawtext="
            f"text='{text}'"
            f"{fontfile}"
            f":fontsize={font_size}"
            ":fontcolor=white"
            ":borderw=5"
            ":bordercolor=black"
            ":x=(w-text_w)/2"
            f":y={y}"
            f":enable='between(t\\,{start:.3f}\\,{end:.3f})'"
        )
    return ",".join(filters)


def probe_video(path: Path) -> tuple[int, int, float]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,duration",
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
    stream = data["streams"][0]
    width = int(stream["width"])
    height = int(stream["height"])
    duration = float(stream.get("duration") or data["format"]["duration"])
    return width, height, duration


def build_edit_plan(moment: Moment, keep_ranges: list[tuple[float, float]]) -> EditPlan:
    rel_words = [
        Word(text=w.text, start=w.start - moment.start, end=w.end - moment.start)
        for w in moment.words
    ]
    rel_captions = chunk_captions(rel_words, min_words=3, max_words=5)
    zooms = plan_zoom_cuts(rel_words)
    if len(zooms) > 24:
        zooms = zooms[:24]
    return EditPlan(moment=moment, captions=rel_captions, zooms=zooms, keep_ranges=keep_ranges)


def _slice_keep_ranges(
    keep_ranges: list[tuple[float, float]], moment_start: float, moment_end: float
) -> list[tuple[float, float]]:
    cursor = 0.0
    slices: list[tuple[float, float]] = []
    for o_start, o_end in keep_ranges:
        dur = o_end - o_start
        c_start, c_end = cursor, cursor + dur
        ov_start = max(c_start, moment_start)
        ov_end = min(c_end, moment_end)
        if ov_end > ov_start + 1e-3:
            off0 = ov_start - c_start
            off1 = ov_end - c_start
            slices.append((o_start + off0, o_start + off1))
        cursor = c_end
        if cursor >= moment_end:
            break
    return slices


def _merge_tiny_gaps(
    slices: list[tuple[float, float]], max_gap: float = 0.12
) -> list[tuple[float, float]]:
    if not slices:
        return []
    merged = [slices[0]]
    for start, end in slices[1:]:
        prev_start, prev_end = merged[-1]
        if start - prev_end <= max_gap:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def render_short(
    source: Path,
    plan: EditPlan,
    output: Path,
    *,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    crf: int = 20,
) -> Path:
    """Rendert einen 9:16 Short mit Zoomcuts und eingebrannten Untertiteln."""
    width, height = even_dimensions(width, height)
    output.parent.mkdir(parents=True, exist_ok=True)

    src_w, src_h, _ = probe_video(source)
    target_aspect = width / height
    if (src_w / src_h) > target_aspect:
        crop_h = src_h
        crop_w = int(src_h * target_aspect)
    else:
        crop_w = src_w
        crop_h = int(src_w / target_aspect)
    crop_w -= crop_w % 2
    crop_h -= crop_h % 2
    crop_x = (src_w - crop_w) // 2
    crop_y = (src_h - crop_h) // 2

    moment_slices = _merge_tiny_gaps(
        _slice_keep_ranges(plan.keep_ranges, plan.moment.start, plan.moment.end)
    )
    if not moment_slices:
        raise ValueError("Keine Medienbereiche für diesen Moment gefunden")

    # Neben Output statt /var/folders — stabilere Pfade auf macOS
    work_dir = output.parent / f".render_{output.stem}"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        parts_video: list[str] = []
        parts_audio: list[str] = []
        filter_parts: list[str] = []
        for i, (start, end) in enumerate(moment_slices):
            filter_parts.append(
                f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS,setsar=1[v{i}]"
            )
            filter_parts.append(
                f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{i}]"
            )
            parts_video.append(f"[v{i}]")
            parts_audio.append(f"[a{i}]")

        n = len(moment_slices)
        filter_parts.append(f"{''.join(parts_video)}concat=n={n}:v=1:a=0[vcat]")
        filter_parts.append(f"{''.join(parts_audio)}concat=n={n}:v=0:a=1[acat]")

        zoom = zoom_expr(plan.zooms, width=width, height=height)
        caption = _caption_filter(plan.captions, work_dir=work_dir, width=width, height=height)

        filter_parts.append(
            f"[vcat]crop={crop_w}:{crop_h}:{crop_x}:{crop_y},"
            f"scale={width}:{height}:flags=lanczos,"
            f"{zoom},"
            f"fps={fps},"
            f"{caption}[vout]"
        )

        # Script-Datei vermeidet Shell/Quote-Probleme bei langen Zoom-Expressions
        script_path = work_dir / "filter.txt"
        script_path.write_text(";\n".join(filter_parts), encoding="utf-8")

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-filter_complex_script",
            str(script_path),
            "-map",
            "[vout]",
            "-map",
            "[acat]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            str(crf),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output),
        ]
        _run(cmd)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return output
