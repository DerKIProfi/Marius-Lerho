from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from shorts_maker.captions import chunk_captions, write_ass
from shorts_maker.effects import even_dimensions, plan_zoom_cuts, zoom_expr
from shorts_maker.models import EditPlan, Moment, Word


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed:\n"
            + " ".join(cmd)
            + "\n"
            + (result.stderr or result.stdout or "unknown error")
        )


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
    captions = chunk_captions(moment.words, min_words=3, max_words=5)
    # Captions relativ zum Moment-Start
    rel_words = [
        Word(text=w.text, start=w.start - moment.start, end=w.end - moment.start) for w in moment.words
    ]
    rel_captions = chunk_captions(rel_words, min_words=3, max_words=5)
    zooms = plan_zoom_cuts(rel_words)
    return EditPlan(moment=moment, captions=rel_captions, zooms=zooms, keep_ranges=keep_ranges)


def _slice_keep_ranges(
    keep_ranges: list[tuple[float, float]], moment_start: float, moment_end: float
) -> list[tuple[float, float]]:
    """Schneidet keep_ranges auf den Moment (Clean-Timeline) und mappt auf Originalzeiten."""
    # keep_ranges sind Originalzeiten. Moment start/end sind Clean-Timeline.
    # Wir bauen Clean->Original Mapping und extrahieren die relevanten Original-Segmente.
    cursor = 0.0
    slices: list[tuple[float, float]] = []
    for o_start, o_end in keep_ranges:
        dur = o_end - o_start
        c_start, c_end = cursor, cursor + dur
        # overlap with [moment_start, moment_end]
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
    # Center-crop auf 9:16 aus dem Quellframe
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

    moment_slices = _slice_keep_ranges(plan.keep_ranges, plan.moment.start, plan.moment.end)
    if not moment_slices:
        raise ValueError("Keine Medienbereiche für diesen Moment gefunden")

    with tempfile.TemporaryDirectory(prefix="shorts_render_") as tmp:
        tmp_path = Path(tmp)
        ass_path = tmp_path / "captions.ass"
        write_ass(ass_path, plan.captions, play_res_x=width, play_res_y=height)

        # Concat über filter_complex select+atrim für präzise Schnitte
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
        # Escape ASS path for ffmpeg (windows-unfriendly chars)
        ass_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")

        filter_parts.append(
            f"[vcat]crop={crop_w}:{crop_h}:{crop_x}:{crop_y},"
            f"scale={width}:{height}:flags=lanczos,"
            f"{zoom},"
            f"fps={fps},"
            f"ass='{ass_escaped}'[vout]"
        )

        filter_complex = ";".join(filter_parts)
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-filter_complex",
            filter_complex,
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

    return output
