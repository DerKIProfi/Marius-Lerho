from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    @property
    def normalized(self) -> str:
        return "".join(ch for ch in self.text.lower() if ch.isalnum() or ch in "äöüß")


@dataclass
class CaptionChunk:
    words: list[Word]
    start: float
    end: float

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


@dataclass
class Moment:
    """Ein Shorts-Kandidat im bereinigten Zeitverlauf."""

    start: float
    end: float
    score: float
    title: str
    words: list[Word] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    @property
    def transcript(self) -> str:
        return " ".join(w.text for w in self.words)


@dataclass
class ZoomKeyframe:
    time: float
    scale: float


@dataclass
class EditPlan:
    moment: Moment
    captions: list[CaptionChunk]
    zooms: list[ZoomKeyframe]
    # Mapping: cleaned timeline -> original media time ranges to keep
    keep_ranges: list[tuple[float, float]]
