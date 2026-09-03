from __future__ import annotations

import json
import subprocess
from pathlib import Path

from shorts_maker.clean import clean_transcript
from shorts_maker.models import Word
from shorts_maker.moments import find_moments
from shorts_maker.render import build_edit_plan, render_short


def _make_source(path: Path, duration: float = 12.0) -> None:
    # 16:9 Testvideo mit Ton
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x1a1a2e:s=1280x720:d={duration}:r=30",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


def test_render_short_end_to_end(tmp_path: Path):
    source = tmp_path / "source.mp4"
    _make_source(source, duration=10.0)

    words = []
    t = 0.2
    script = "Das ist ein wichtiger Tipp Warum das niemand kennt Sofort handeln".split()
    for token in script:
        words.append(Word(text=token, start=t, end=t + 0.35))
        t += 0.45
        if token.lower() in {"äh", "ähm"}:
            continue
        if len(words) % 4 == 0:
            t += 0.9  # Pause

    # Fülllaute einstreuen
    words.insert(3, Word(text="äh", start=1.4, end=1.7))
    words.append(Word(text="ähm", start=t, end=t + 0.3))

    cleaned = clean_transcript(words, max_pause=0.35)
    moments = find_moments(
        cleaned.words,
        target_duration=8,
        min_duration=3,
        max_duration=12,
        max_shorts=1,
    )
    assert moments
    plan = build_edit_plan(moments[0], cleaned.keep_ranges)
    out = tmp_path / "short.mp4"
    render_short(source, plan, out, width=720, height=1280, fps=24, crf=28)
    assert out.exists()
    assert out.stat().st_size > 1000

    # ffprobe: 9:16
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    stream = json.loads(probe.stdout)["streams"][0]
    assert stream["width"] == 720
    assert stream["height"] == 1280
