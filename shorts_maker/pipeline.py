from __future__ import annotations

import json
from pathlib import Path

from shorts_maker.clean import clean_transcript
from shorts_maker.download import download_video
from shorts_maker.moments import find_moments, score_label
from shorts_maker.render import build_edit_plan, render_short
from shorts_maker.transcribe import load_transcript, save_transcript, transcribe


def run_pipeline(
    url_or_path: str,
    output_dir: Path,
    *,
    language: str | None = "de",
    model_size: str = "base",
    max_shorts: int = 3,
    target_duration: float = 35.0,
    min_duration: float = 15.0,
    max_duration: float = 59.0,
    max_pause: float = 0.35,
    width: int = 1080,
    height: int = 1920,
    skip_download: bool = False,
) -> dict:
    """Komplette Pipeline: Download → Transcribe → Clean → Select → Render."""
    output_dir = Path(output_dir)
    work = output_dir / "work"
    shorts_dir = output_dir / "shorts"
    work.mkdir(parents=True, exist_ok=True)
    shorts_dir.mkdir(parents=True, exist_ok=True)

    source = Path(url_or_path)
    if source.exists() and source.is_file():
        video_path = source
    else:
        if skip_download:
            raise FileNotFoundError(f"Lokale Datei nicht gefunden: {url_or_path}")
        print("↓ Lade Video …")
        video_path = download_video(url_or_path, work / "download")

    transcript_path = work / "transcript.json"
    if transcript_path.exists():
        print("◎ Transkript gefunden, überspringe Whisper …")
        words = load_transcript(transcript_path)
    else:
        print(f"◎ Transkribiere mit Whisper ({model_size}) …")
        words = transcribe(video_path, model_size=model_size, language=language)
        save_transcript(words, transcript_path)

    print("✂ Entferne Pausen & Fülllaute …")
    cleaned = clean_transcript(words, max_pause=max_pause)
    save_transcript(cleaned.words, work / "transcript_clean.json")
    (work / "keep_ranges.json").write_text(
        json.dumps(cleaned.keep_ranges, indent=2), encoding="utf-8"
    )
    print(
        f"  → {cleaned.removed_fillers} Fülllaute, "
        f"{cleaned.removed_pause_seconds:.1f}s Pausen entfernt"
    )

    print("★ Wähle interessante Momente …")
    moments = find_moments(
        cleaned.words,
        target_duration=target_duration,
        min_duration=min_duration,
        max_duration=max_duration,
        max_shorts=max_shorts,
    )
    if not moments:
        raise RuntimeError("Keine geeigneten Shorts-Momente gefunden.")

    results = []
    for idx, moment in enumerate(moments, start=1):
        label = score_label(moment.score)
        print(f"→ Short {idx}/{len(moments)} [{label}] {moment.duration:.1f}s — {moment.title}")
        plan = build_edit_plan(moment, cleaned.keep_ranges)
        out_name = f"short_{idx:02d}_{_slug(moment.title)}.mp4"
        out_path = shorts_dir / out_name
        render_short(video_path, plan, out_path, width=width, height=height)
        meta = {
            "file": str(out_path),
            "title": moment.title,
            "score": moment.score,
            "duration": moment.duration,
            "start": moment.start,
            "end": moment.end,
            "captions": len(plan.captions),
            "zooms": len(plan.zooms),
            "transcript": moment.transcript,
        }
        results.append(meta)
        (shorts_dir / f"short_{idx:02d}.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    summary = {
        "source": str(video_path),
        "removed_fillers": cleaned.removed_fillers,
        "removed_pause_seconds": cleaned.removed_pause_seconds,
        "shorts": results,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"✓ Fertig: {len(results)} Short(s) in {shorts_dir}")
    return summary


def _slug(text: str, max_len: int = 40) -> str:
    import re

    s = re.sub(r"[^\w\-]+", "_", text.strip(), flags=re.UNICODE).strip("_").lower()
    return (s or "clip")[:max_len]
