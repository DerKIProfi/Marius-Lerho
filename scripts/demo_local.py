#!/usr/bin/env python3
"""Erzeugt ein lokales Demo-Video + Transkript und rendert Shorts ohne YouTube/Whisper."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shorts_maker.models import Word
from shorts_maker.pipeline import run_pipeline
from shorts_maker.transcribe import save_transcript


SCRIPT = [
    (0.4, "Warum"),
    (0.8, "das"),
    (1.1, "niemand"),
    (1.5, "weiß"),
    (1.9, "äh"),
    (2.5, "dieser"),
    (2.9, "Fehler"),
    (3.4, "kostet"),
    (3.8, "dich"),
    (4.2, "Zeit"),
    (4.6, "und"),
    (5.0, "Geld"),
    (5.5, "ähm"),
    (6.4, "Du"),
    (6.7, "musst"),
    (7.1, "sofort"),
    (7.6, "umdenken"),
    (8.3, "und"),
    (8.6, "nie"),
    (9.0, "wieder"),
    (9.5, "raten"),
    (10.2, "Stattdessen"),
    (10.8, "nutze"),
    (11.2, "diesen"),
    (11.6, "einfachen"),
    (12.1, "Tipp"),
    (12.6, "jeden"),
    (13.0, "Tag"),
]


def make_video(path: Path, duration: float = 14.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # 16:9 „Talking head“ Simulation: Gradient + Titelbox
    filter_complex = (
        "color=c=0x0b1320:s=1280x720:d={dur}:r=30[bg];"
        "[bg]drawbox=x=480:y=120:w=320:h=420:color=0x1c2541:t=fill,"
        "drawbox=x=560:y=200:w=160:h=160:color=0x5bc0be:t=fill,"
        "drawtext=text='DEMO TALK':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=40,"
        "drawtext=text='16\\:9 Source':fontsize=28:fontcolor=0x94a3b8:x=(w-text_w)/2:y=660[vout]"
    ).format(dur=duration)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-filter_complex",
            filter_complex,
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=196:duration={duration}",
            "-map",
            "[vout]",
            "-map",
            "0:a",
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
        text=True,
    )


def main() -> None:
    out = ROOT / "output" / "demo"
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)
    video = work / "demo_source.mp4"
    make_video(video)

    words = []
    for start, text in SCRIPT:
        words.append(Word(text=text, start=start, end=start + 0.32))
    # lange Pause künstlich
    words.append(Word(text="Achtung", start=15.5, end=15.9))
    words.append(Word(text="das", start=16.1, end=16.35))
    words.append(Word(text="ändert", start=16.45, end=16.85))
    words.append(Word(text="alles", start=16.95, end=17.4))

    # Video etwas länger machen für zweite Phrase
    make_video(video, duration=18.0)
    save_transcript(words, work / "transcript.json")

    summary = run_pipeline(
        str(video),
        out,
        language="de",
        model_size="tiny",
        max_shorts=2,
        target_duration=12,
        min_duration=5,
        max_duration=20,
        max_pause=0.35,
        width=720,
        height=1280,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
