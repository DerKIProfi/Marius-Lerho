from __future__ import annotations

import re
from collections.abc import Iterable

from shorts_maker.models import Moment, Word

HOOK_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bwarum\b",
        r"\bwie\b",
        r"\bgeheimnis\b",
        r"\btipp\b",
        r"\bfehler\b",
        r"\bniemand\b",
        r"\bwichtig\b",
        r"\bsofort\b",
        r"\bnie\b",
        r"\bimmer\b",
        r"\bmusst\b",
        r"\bsolltest\b",
        r"\bcheck\b",
        r"\bwatch\b",
        r"\bsecret\b",
        r"\bmistake\b",
        r"\bwhy\b",
        r"\bhow to\b",
        r"\bnever\b",
        r"\balways\b",
        r"\bstopp?\b",
        r"\bachtung\b",
        r"[!?]",
    ]
]


def _density(words: list[Word]) -> float:
    if not words:
        return 0.0
    duration = max(0.1, words[-1].end - words[0].start)
    chars = sum(len(w.text) for w in words)
    return chars / duration


def _hook_score(text: str) -> float:
    score = 0.0
    for pattern in HOOK_PATTERNS:
        if pattern.search(text):
            score += 1.0
    return min(score, 6.0)


def _window_score(words: list[Word]) -> float:
    if not words:
        return 0.0
    text = " ".join(w.text for w in words)
    dens = _density(words)
    hooks = _hook_score(text)
    # leichte Bevorzugung früherer Abschnitte (Hook-Potenzial)
    early_bonus = 1.0 / (1.0 + words[0].start / 120.0)
    length = words[-1].end - words[0].start
    length_penalty = 0.0
    if length < 12:
        length_penalty = (12 - length) * 0.4
    elif length > 55:
        length_penalty = (length - 55) * 0.15
    return dens * 0.35 + hooks * 1.4 + early_bonus * 1.2 - length_penalty


def _title_from_words(words: Iterable[Word], max_words: int = 8) -> str:
    parts = [w.text.strip(".,;:") for w in words if w.text.strip()]
    title = " ".join(parts[:max_words]).strip()
    return title[:72] or "Short"


def find_moments(
    words: list[Word],
    *,
    target_duration: float = 35.0,
    min_duration: float = 15.0,
    max_duration: float = 59.0,
    max_shorts: int = 3,
    stride: float = 4.0,
) -> list[Moment]:
    """Findet interessante Shorts-Abschnitte in der bereinigten Timeline."""
    if not words:
        return []

    total_end = words[-1].end
    if total_end <= max_duration and total_end >= min_duration:
        return [
            Moment(
                start=words[0].start,
                end=words[-1].end,
                score=_window_score(words),
                title=_title_from_words(words),
                words=list(words),
            )
        ]

    candidates: list[Moment] = []
    t = words[0].start
    while t + min_duration <= total_end + 1e-6:
        end_target = min(t + target_duration, total_end)
        window = [w for w in words if w.start >= t - 1e-3 and w.end <= end_target + 1e-3]
        if len(window) >= 6:
            # snappe auf Wortgrenzen
            start = window[0].start
            end = min(window[-1].end + 0.15, start + max_duration)
            clipped = [w for w in window if w.end <= end + 1e-3]
            if clipped and (end - start) >= min_duration:
                score = _window_score(clipped)
                candidates.append(
                    Moment(
                        start=start,
                        end=end,
                        score=score,
                        title=_title_from_words(clipped),
                        words=clipped,
                    )
                )
        t += stride

    # Non-maximum suppression: überlappende Clips vermeiden
    candidates.sort(key=lambda m: m.score, reverse=True)
    selected: list[Moment] = []
    for cand in candidates:
        if len(selected) >= max_shorts:
            break
        overlap = False
        for other in selected:
            inter = max(0.0, min(cand.end, other.end) - max(cand.start, other.start))
            if inter / min(cand.duration, other.duration) > 0.35:
                overlap = True
                break
        if not overlap:
            selected.append(cand)

    selected.sort(key=lambda m: m.start)
    return selected


def score_label(score: float) -> str:
    if score >= 8:
        return "hot"
    if score >= 5:
        return "good"
    return "ok"
