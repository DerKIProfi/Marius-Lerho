from __future__ import annotations

from dataclasses import dataclass

from shorts_maker.models import Word

# Deutsche + englische Fülllaute / Verzögerungswörter
DEFAULT_FILLERS = frozenset(
    {
        "äh",
        "ähm",
        "ähm.",
        "ääh",
        "eh",
        "ehm",
        "hm",
        "hmm",
        "mhm",
        "uh",
        "uhh",
        "um",
        "umm",
        "erm",
        "uhuh",
        "yeah",
        "soo",
        "also",  # oft als Füllwort – wird nur entfernt wenn isoliert kurz
        "like",
        "basically",
        "literally",
        "youknow",
        "irgendwie",
        "halt",
        "ne",
        "nee",
        "naja",
    }
)

# Wörter die nur als Filler gelten wenn sie allein stehen / sehr kurz sind
CONTEXTUAL_FILLERS = frozenset({"also", "halt", "ja", "okay", "ok", "so", "like", "right"})


@dataclass
class CleanResult:
    words: list[Word]  # neu getimte Wörter (kontinuierliche Timeline ohne Pausen)
    keep_ranges: list[tuple[float, float]]  # Original-Zeitbereiche die behalten werden
    removed_fillers: int
    removed_pause_seconds: float


def _is_filler(word: Word, fillers: frozenset[str]) -> bool:
    norm = word.normalized
    if not norm:
        return True
    if norm in fillers:
        # Kontextuelle Filler nur entfernen wenn sehr kurz
        if norm in CONTEXTUAL_FILLERS and word.duration > 0.45:
            return False
        return True
    return False


def clean_transcript(
    words: list[Word],
    *,
    max_pause: float = 0.35,
    fillers: frozenset[str] | None = None,
    pad: float = 0.04,
) -> CleanResult:
    """Entfernt Fülllaute und lange Pausen; baut eine kompakte Timeline.

    Rückgabe:
      - words: Wörter mit neuen start/end auf der bereinigten Timeline
      - keep_ranges: Original-Medienbereiche die beim Rendern behalten werden
    """
    filler_set = fillers if fillers is not None else DEFAULT_FILLERS
    kept_original: list[Word] = []
    removed_fillers = 0

    for w in words:
        if _is_filler(w, filler_set):
            removed_fillers += 1
            continue
        kept_original.append(w)

    if not kept_original:
        return CleanResult(words=[], keep_ranges=[], removed_fillers=removed_fillers, removed_pause_seconds=0.0)

    # Original-Keep-Ranges zusammenfassen (Wörter + kleine Pads, Pausen > max_pause schneiden)
    ranges: list[tuple[float, float]] = []
    removed_pause = 0.0

    for i, w in enumerate(kept_original):
        start = max(0.0, w.start - pad)
        end = w.end + pad
        if not ranges:
            ranges.append((start, end))
            continue

        prev_start, prev_end = ranges[-1]
        gap = start - prev_end
        if gap <= max_pause:
            ranges[-1] = (prev_start, max(prev_end, end))
        else:
            removed_pause += max(0.0, gap - max_pause)
            # kleine Bridge-Pause behalten für natürlichen Rhythmus
            bridge_end = prev_end + min(max_pause, gap)
            ranges[-1] = (prev_start, bridge_end)
            ranges.append((start, end))

    # Mapping Original -> Clean Timeline
    clean_words: list[Word] = []
    cursor = 0.0
    range_idx = 0
    # Precompute cumulative offsets
    range_offsets: list[tuple[float, float, float]] = []  # orig_start, orig_end, clean_start
    for orig_start, orig_end in ranges:
        range_offsets.append((orig_start, orig_end, cursor))
        cursor += orig_end - orig_start

    def to_clean(t: float) -> float:
        for o_start, o_end, c_start in range_offsets:
            if o_start - 1e-3 <= t <= o_end + 1e-3:
                return c_start + max(0.0, min(t, o_end) - o_start)
        # Fallback: nächstes Range
        for o_start, o_end, c_start in range_offsets:
            if t < o_start:
                return c_start
        if range_offsets:
            o_start, o_end, c_start = range_offsets[-1]
            return c_start + (o_end - o_start)
        return t

    for w in kept_original:
        clean_words.append(
            Word(
                text=w.text,
                start=to_clean(w.start),
                end=max(to_clean(w.start) + 0.05, to_clean(w.end)),
            )
        )

    return CleanResult(
        words=clean_words,
        keep_ranges=ranges,
        removed_fillers=removed_fillers,
        removed_pause_seconds=removed_pause,
    )


def original_time_at(clean_t: float, keep_ranges: list[tuple[float, float]]) -> float:
    """Mappt bereinigte Zeit zurück auf Original-Medienzeit."""
    cursor = 0.0
    for o_start, o_end in keep_ranges:
        dur = o_end - o_start
        if clean_t <= cursor + dur:
            return o_start + (clean_t - cursor)
        cursor += dur
    if keep_ranges:
        return keep_ranges[-1][1]
    return clean_t
