from __future__ import annotations

import json
from pathlib import Path

from shorts_maker.models import Word


def _is_plausible_word(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    # Mindestens ein Buchstabe/Zahl (auch DE-Umlaute)
    if not any(ch.isalnum() for ch in cleaned):
        return False
    # Extrem kurze Artefakte wie "." "," "-"
    letters = sum(1 for ch in cleaned if ch.isalpha())
    if letters == 0 and len(cleaned) <= 2:
        return False
    return True


def transcribe(
    video_path: Path,
    *,
    model_size: str = "small",
    language: str | None = "de",
    device: str = "cpu",
    compute_type: str = "int8",
    min_word_prob: float = 0.42,
    min_segment_logprob: float = -1.15,
) -> list[Word]:
    """Transkribiert mit word-level Timestamps via faster-whisper.

    Filtert unsichere Whisper-Wörter heraus, damit Untertitel nicht voller
    Konzert-/Musik-Halluzinationen sind.
    """
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    prompt = None
    if language == "de":
        prompt = "Willkommen. Das ist ein Gespräch auf Deutsch mit klarer Aussprache."
    elif language == "en":
        prompt = "Welcome. This is a clear conversational English recording."

    segments, _info = model.transcribe(
        str(video_path),
        language=language,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={
            "min_silence_duration_ms": 500,
            "speech_pad_ms": 250,
        },
        beam_size=5,
        best_of=5,
        patience=1.0,
        condition_on_previous_text=True,
        initial_prompt=prompt,
        temperature=0.0,
    )

    words: list[Word] = []
    for segment in segments:
        if getattr(segment, "avg_logprob", 0.0) < min_segment_logprob:
            continue
        if not segment.words:
            text = (segment.text or "").strip()
            if text and _is_plausible_word(text):
                words.append(Word(text=text, start=float(segment.start), end=float(segment.end)))
            continue
        for w in segment.words:
            text = (w.word or "").strip()
            if not _is_plausible_word(text):
                continue
            prob = getattr(w, "probability", None)
            if prob is not None and prob < min_word_prob:
                continue
            # verworfene Extremkurz-Halluzinationen
            if (float(w.end) - float(w.start)) < 0.04 and len(text) <= 1:
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
