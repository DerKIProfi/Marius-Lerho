from __future__ import annotations

import json
from pathlib import Path

from shorts_maker.models import Word


def transcribe(
    video_path: Path,
    *,
    model_size: str = "base",
    language: str | None = "de",
    device: str = "cpu",
    compute_type: str = "int8",
) -> list[Word]:
    """Transkribiert mit word-level Timestamps via faster-whisper."""
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, _info = model.transcribe(
        str(video_path),
        language=language,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 400},
    )

    words: list[Word] = []
    for segment in segments:
        if not segment.words:
            # Fallback: ganze Segment-Zeitspanne
            text = (segment.text or "").strip()
            if text:
                words.append(Word(text=text, start=float(segment.start), end=float(segment.end)))
            continue
        for w in segment.words:
            text = (w.word or "").strip()
            if not text:
                continue
            words.append(Word(text=text, start=float(w.start), end=float(w.end)))
    return words


def save_transcript(words: list[Word], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [{"text": w.text, "start": w.start, "end": w.end} for w in words]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_transcript(path: Path) -> list[Word]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Word(text=item["text"], start=float(item["start"]), end=float(item["end"])) for item in data]
