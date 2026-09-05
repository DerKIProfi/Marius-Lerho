"""Stabiles Public API für App-Integration (Social Media / Backend / Jobs).

Codex und App-Code sollten bevorzugt über dieses Modul gehen,
nicht über interne Modulpfade.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from shorts_maker.pipeline import run_pipeline

__all__ = [
    "ShortClip",
    "PipelineResult",
    "PipelineOptions",
    "generate_shorts",
]


@dataclass
class PipelineOptions:
    """Optionen für die Shorts-Pipeline."""

    language: str | None = "de"
    model_size: str = "base"
    max_shorts: int = 3
    target_duration: float = 35.0
    min_duration: float = 15.0
    max_duration: float = 59.0
    max_pause: float = 0.35
    width: int = 1080
    height: int = 1920


@dataclass
class ShortClip:
    """Ein fertiger Short inklusive Metadaten."""

    file: str
    title: str
    score: float
    duration: float
    start: float
    end: float
    captions: int
    zooms: int
    transcript: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShortClip:
        return cls(
            file=str(data["file"]),
            title=str(data.get("title") or ""),
            score=float(data.get("score") or 0.0),
            duration=float(data.get("duration") or 0.0),
            start=float(data.get("start") or 0.0),
            end=float(data.get("end") or 0.0),
            captions=int(data.get("captions") or 0),
            zooms=int(data.get("zooms") or 0),
            transcript=str(data.get("transcript") or ""),
        )


@dataclass
class PipelineResult:
    """Ergebnis einer kompletten Generate-Runs."""

    source: str
    removed_fillers: int
    removed_pause_seconds: float
    shorts: list[ShortClip] = field(default_factory=list)
    summary_path: str | None = None
    output_dir: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "removed_fillers": self.removed_fillers,
            "removed_pause_seconds": self.removed_pause_seconds,
            "shorts": [asdict(s) for s in self.shorts],
            "summary_path": self.summary_path,
            "output_dir": self.output_dir,
        }


def generate_shorts(
    url_or_path: str,
    output_dir: str | Path,
    options: PipelineOptions | None = None,
) -> PipelineResult:
    """Erzeugt Shorts aus YouTube-URL oder lokaler Videodatei.

    Das ist der empfohlene Einstiegspunkt für App-/Backend-Integration.

    Args:
        url_or_path: YouTube-URL oder Pfad zu einer lokalen Videodatei.
        output_dir: Zielordner (enthält danach ``work/``, ``shorts/``, ``summary.json``).
        options: optionale Pipeline-Parameter.

    Returns:
        Strukturiertes ``PipelineResult`` mit Pfaden und Metadaten.
    """
    opts = options or PipelineOptions()
    out = Path(output_dir)
    raw = run_pipeline(
        url_or_path,
        out,
        language=opts.language,
        model_size=opts.model_size,
        max_shorts=opts.max_shorts,
        target_duration=opts.target_duration,
        min_duration=opts.min_duration,
        max_duration=opts.max_duration,
        max_pause=opts.max_pause,
        width=opts.width,
        height=opts.height,
    )
    clips = [ShortClip.from_dict(item) for item in raw.get("shorts", [])]
    return PipelineResult(
        source=str(raw.get("source") or ""),
        removed_fillers=int(raw.get("removed_fillers") or 0),
        removed_pause_seconds=float(raw.get("removed_pause_seconds") or 0.0),
        shorts=clips,
        summary_path=str(out / "summary.json"),
        output_dir=str(out),
    )
