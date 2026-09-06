from __future__ import annotations

import re
from collections.abc import Iterable

from shorts_maker.models import Moment, Word

HOOK_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bwarum\b",
        r"\bwieso\b",
        r"\bweshalb\b",
        r"\bgeheimnis\b",
        r"\btipp\b",
        r"\bfehler\b",
        r"\bniemand\b",
        r"\bwichtig\b",
        r"\bsofort\b",
        r"\bpass\s*auf\b",
        r"\bschau\b",
        r"\bhör\b",
        r"\bmusst\b",
        r"\bsolltest\b",
        r"\bnie\b",
        r"\bimmer\b",
        r"\bcheck\b",
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


def _speech_clusters(words: list[Word], max_gap: float) -> list[list[Word]]:
    """Gruppiert Wörter in zusammenhängende Sprechblasen (Originalzeit)."""
    if not words:
        return []
    clusters: list[list[Word]] = [[words[0]]]
    for w in words[1:]:
        if w.start - clusters[-1][-1].end <= max_gap:
            clusters[-1].append(w)
        else:
            clusters.append([w])
    return clusters


def _density(words: list[Word]) -> float:
    if not words:
        return 0.0
    duration = max(0.1, words[-1].end - words[0].start)
    chars = sum(len(w.text) for w in words)
    return chars / duration


def _speech_ratio(words: list[Word]) -> float:
    if not words:
        return 0.0
    span = max(0.1, words[-1].end - words[0].start)
    spoken = sum(w.duration for w in words)
    return min(1.0, spoken / span)


def _max_internal_gap(words: list[Word]) -> float:
    if len(words) < 2:
        return 0.0
    return max(words[i + 1].start - words[i].end for i in range(len(words) - 1))


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
    ratio = _speech_ratio(words)
    length = words[-1].end - words[0].start
    length_penalty = 0.0
    if length < 12:
        length_penalty = (12 - length) * 0.5
    elif length > 55:
        length_penalty = (length - 55) * 0.2
    # Bestrafe löchrige Abschnitte (würden zu sinnlosen Jumpcuts)
    gap_penalty = max(0.0, _max_internal_gap(words) - 1.5) * 1.5
    return dens * 0.25 + hooks * 1.3 + ratio * 4.0 - length_penalty - gap_penalty


def _title_from_words(words: Iterable[Word], max_words: int = 8) -> str:
    parts = [w.text.strip(".,;:!?") for w in words if w.text.strip()]
    # Skip leading filler-ish tokens in titles
    skip = {"ja", "also", "und", "äh", "ähm", "ok", "okay", "so"}
    while parts and parts[0].lower() in skip:
        parts.pop(0)
    title = " ".join(parts[:max_words]).strip()
    return title[:72] or "Short"


def find_moments(
    words: list[Word],
    *,
    target_duration: float = 35.0,
    min_duration: float = 15.0,
    max_duration: float = 59.0,
    max_shorts: int = 3,
    stride: float = 3.0,
    max_gap: float = 2.0,
    min_words: int = 10,
) -> list[Moment]:
    """Findet zusammenhängende Shorts-Abschnitte in der Original-Timeline.

    Wichtig: Es werden nur Abschnitte gewählt, deren Wörter in Originalzeit
    zusammenhängen (keine Sprünge quer durchs Video).
    """
    if not words:
        return []

    clusters = _speech_clusters(words, max_gap=max_gap)
    candidates: list[Moment] = []

    for cluster in clusters:
        if len(cluster) < min_words:
            continue
        cluster_start = cluster[0].start
        cluster_end = cluster[-1].end
        span = cluster_end - cluster_start
        if span < min_duration * 0.6 and sum(w.duration for w in cluster) < min_duration * 0.45:
            continue

        # Kurzer Cluster: ggf. als Ganzes nehmen
        if span <= max_duration and span >= min_duration and len(cluster) >= min_words:
            if _max_internal_gap(cluster) <= max_gap:
                candidates.append(
                    Moment(
                        start=cluster_start,
                        end=cluster_end,
                        score=_window_score(cluster),
                        title=_title_from_words(cluster),
                        words=list(cluster),
                    )
                )

        # Längere Cluster: gleitende Fenster in Originalzeit
        t = cluster_start
        while t + min_duration <= cluster_end + 1e-6:
            end_target = min(t + target_duration, cluster_end)
            window = [w for w in cluster if w.start >= t - 1e-3 and w.end <= end_target + 1e-3]
            if len(window) >= min_words:
                start = window[0].start
                end = min(window[-1].end + 0.12, start + max_duration)
                clipped = [w for w in window if w.end <= end + 1e-3]
                if (
                    clipped
                    and (end - start) >= min_duration
                    and _max_internal_gap(clipped) <= max_gap
                ):
                    candidates.append(
                        Moment(
                            start=start,
                            end=end,
                            score=_window_score(clipped),
                            title=_title_from_words(clipped),
                            words=clipped,
                        )
                    )
            t += stride

    candidates.sort(key=lambda m: m.score, reverse=True)
    selected: list[Moment] = []
    for cand in candidates:
        if len(selected) >= max_shorts:
            break
        overlaps = False
        for other in selected:
            inter = max(0.0, min(cand.end, other.end) - max(cand.start, other.start))
            if inter / min(cand.duration, other.duration) > 0.3:
                overlaps = True
                break
        if not overlaps:
            selected.append(cand)

    selected.sort(key=lambda m: m.start)
    return selected


def score_label(score: float) -> str:
    if score >= 8:
        return "hot"
    if score >= 5:
        return "good"
    return "ok"
