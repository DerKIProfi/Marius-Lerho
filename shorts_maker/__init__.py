"""YouTube → Shorts: automatische 9:16 Clips mit Zoomcuts und Untertiteln."""

from shorts_maker.api import (
    PipelineOptions,
    PipelineResult,
    ShortClip,
    generate_shorts,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "PipelineOptions",
    "PipelineResult",
    "ShortClip",
    "generate_shorts",
]
