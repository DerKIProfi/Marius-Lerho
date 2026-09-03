from __future__ import annotations

from pathlib import Path

import click

from shorts_maker import __version__
from shorts_maker.pipeline import run_pipeline


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("url_or_path")
@click.option(
    "-o",
    "--output",
    "output_dir",
    type=click.Path(path_type=Path),
    default=Path("output"),
    show_default=True,
    help="Ausgabeordner für Shorts und Zwischenstände",
)
@click.option("--language", default="de", show_default=True, help="Whisper-Sprache (z.B. de, en, auto)")
@click.option(
    "--model",
    "model_size",
    default="base",
    show_default=True,
    type=click.Choice(["tiny", "base", "small", "medium", "large-v3"], case_sensitive=False),
    help="Whisper-Modellgröße",
)
@click.option("--max-shorts", default=3, show_default=True, help="Maximale Anzahl Shorts")
@click.option("--duration", default=35.0, show_default=True, help="Ziel-Länge pro Short in Sekunden")
@click.option("--min-duration", default=15.0, show_default=True, help="Minimale Short-Länge")
@click.option("--max-duration", default=59.0, show_default=True, help="Maximale Short-Länge")
@click.option("--max-pause", default=0.35, show_default=True, help="Max. Pause zwischen Wörtern (s)")
@click.option("--width", default=1080, show_default=True)
@click.option("--height", default=1920, show_default=True)
@click.version_option(__version__, prog_name="shorts-maker")
def main(
    url_or_path: str,
    output_dir: Path,
    language: str,
    model_size: str,
    max_shorts: int,
    duration: float,
    min_duration: float,
    max_duration: float,
    max_pause: float,
    width: int,
    height: int,
) -> None:
    """Erzeugt Shorts (9:16) aus einem YouTube-Link oder einer lokalen Videodatei.

    Entfernt Pausen/Fülllaute, wählt spannende Momente, setzt Zoomcuts
    und synchronisierte Untertitel (3–5 Wörter).
    """
    lang = None if language.lower() in {"auto", "none"} else language
    run_pipeline(
        url_or_path,
        output_dir,
        language=lang,
        model_size=model_size,
        max_shorts=max_shorts,
        target_duration=duration,
        min_duration=min_duration,
        max_duration=max_duration,
        max_pause=max_pause,
        width=width,
        height=height,
    )


if __name__ == "__main__":
    main()
