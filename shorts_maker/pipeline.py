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
    model_size: str = "small",
    max_shorts: int = 3,
    target_duration: float = 35.0,
    min_duration: float = 15.0,
    max_duration: float = 59.0,
    max_pause: float = 0.55,
    max_gap: float = 2.0,
    width: int = 1080,
    height: int = 1920,
    skip_download: bool = False,
    force_transcribe: bool = False,
) -> dict:
    """Komplette Pipeline: Download → Transcribe → Select → Clean → Render.

    Reihenfolge ist bewusst: erst zusammenhängende Momente in Originalzeit
    wählen, dann nur innerhalb jedes Moments Pausen/Fülllaute kürzen.
    So entstehen keine Sprünge quer durchs Video.
    """
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
    if transcript_path.exists() and not force_transcribe:
        print("◎ Transkript gefunden, überspringe Whisper …")
        print("  (neu transkribieren: --force-transcribe)")
        words = load_transcript(transcript_path)
    else:
        print(f"◎ Transkribiere mit Whisper ({model_size}) …")
        words = transcribe(video_path, model_size=model_size, language=language)
        save_transcript(words, transcript_path)

    if not words:
        raise RuntimeError(
            "Keine brauchbaren Wörter im Transkript. "
            "Versuch: --model small oder --model medium und --force-transcribe"
        )

    print("★ Wähle zusammenhängende Momente (Originalzeit) …")
    moments = find_moments(
        words,
        target_duration=target_duration,
        min_duration=min_duration,
        max_duration=max_duration,
        max_shorts=max_shorts,
        max_gap=max_gap,
    )
    if not moments:
        raise RuntimeError(
            "Keine zusammenhängenden Shorts-Momente gefunden. "
            "Tipp: --max-gap 3 --min-duration 12 --model small --force-transcribe"
        )

    results = []
    total_fillers = 0
    total_pauses = 0.0

    for idx, moment in enumerate(moments, start=1):
        label = score_label(moment.score)
        print(
            f"→ Short {idx}/{len(moments)} [{label}] "
            f"Roh {moment.duration:.1f}s @ {moment.start:.1f}–{moment.end:.1f}s — {moment.title}"
        )

        # Nur INNERHALB des Moments säubern → keine Querschnitte durchs Video
        cleaned = clean_transcript(moment.words, max_pause=max_pause)
        total_fillers += cleaned.removed_fillers
        total_pauses += cleaned.removed_pause_seconds
        if len(cleaned.words) < 6:
            print("  ⚠ Zu wenig Klartext nach Clean — überspringe")
            continue

        # Captions/Zooms auf bereinigter Timeline (startet nahe 0)
        from shorts_maker.models import Moment as MomentModel

        clean_moment = MomentModel(
            start=cleaned.words[0].start,
            end=cleaned.words[-1].end,
            score=moment.score,
            title=_title_prefer_clean(cleaned.words, moment.title),
            words=cleaned.words,
        )
        print(
            f"  ✂ Clean: {cleaned.removed_fillers} Fülllaute, "
            f"{cleaned.removed_pause_seconds:.1f}s Pausen → {clean_moment.duration:.1f}s"
        )

        plan = build_edit_plan(clean_moment, cleaned.keep_ranges)
        # Guard: keep_ranges dürfen nicht über das ganze Video springen
        if cleaned.keep_ranges:
            span = cleaned.keep_ranges[-1][1] - cleaned.keep_ranges[0][0]
            kept = sum(e - s for s, e in cleaned.keep_ranges)
            if span > 0 and kept / span < 0.35:
                print("  ⚠ Abschnitt zu löchrig — überspringe")
                continue

        out_name = f"short_{idx:02d}_{_slug(clean_moment.title)}.mp4"
        out_path = shorts_dir / out_name
        render_short(video_path, plan, out_path, width=width, height=height)
        meta = {
            "file": str(out_path),
            "title": clean_moment.title,
            "score": clean_moment.score,
            "duration": clean_moment.duration,
            "source_start": moment.start,
            "source_end": moment.end,
            "captions": len(plan.captions),
            "zooms": len(plan.zooms),
            "transcript": clean_moment.transcript,
            "keep_ranges": cleaned.keep_ranges,
        }
        results.append(meta)
        (shorts_dir / f"short_{idx:02d}.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    if not results:
        raise RuntimeError("Alle Moment-Kandidaten wurden verworfen — Transkript prüfen.")

    summary = {
        "source": str(video_path),
        "removed_fillers": total_fillers,
        "removed_pause_seconds": total_pauses,
        "shorts": results,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"✓ Fertig: {len(results)} Short(s) in {shorts_dir}")
    return summary


def _title_prefer_clean(words, fallback: str) -> str:
    parts = [w.text.strip(".,;:!?") for w in words if w.text.strip()]
    skip = {"ja", "also", "und", "äh", "ähm", "ok", "okay", "so", "ne", "nee"}
    while parts and parts[0].lower() in skip:
        parts.pop(0)
    title = " ".join(parts[:8]).strip()
    return (title[:72] if title else fallback) or "Short"


def _slug(text: str, max_len: int = 40) -> str:
    import re

    s = re.sub(r"[^\w\-]+", "_", text.strip(), flags=re.UNICODE).strip("_").lower()
    return (s or "clip")[:max_len]
