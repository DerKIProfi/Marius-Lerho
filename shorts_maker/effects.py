from __future__ import annotations

from shorts_maker.models import ZoomKeyframe, Word


def plan_zoom_cuts(
    words: list[Word],
    *,
    base_scale: float = 1.0,
    punch_scale: float = 1.18,
    hard_punch: float = 1.28,
) -> list[ZoomKeyframe]:
    """Plant moderne Zoomcuts: Punch-Ins an Satzanfängen und Emphasis-Wörtern."""
    if not words:
        return [ZoomKeyframe(time=0.0, scale=base_scale)]

    zooms: list[ZoomKeyframe] = [ZoomKeyframe(time=max(0.0, words[0].start - 0.05), scale=base_scale)]
    emphasis = {
        "nie",
        "immer",
        "sofort",
        "wichtig",
        "fehler",
        "stopp",
        "stop",
        "warum",
        "geheimnis",
        "never",
        "always",
        "secret",
        "mistake",
        "wait",
        "achtung",
    }

    last_zoom_t = -10.0
    for i, w in enumerate(words):
        is_sentence_start = i == 0 or words[i - 1].text.rstrip().endswith((".", "!", "?", ":"))
        is_emphasis = w.normalized in emphasis or w.text.rstrip().endswith("!")
        gap_ok = (w.start - last_zoom_t) >= 1.1

        if gap_ok and (is_sentence_start or is_emphasis):
            scale = hard_punch if is_emphasis else punch_scale
            # leichter Wechsel: abwechselnd etwas stärker / schwächer
            if len(zooms) % 2 == 0:
                scale = min(scale + 0.04, 1.35)
            zooms.append(ZoomKeyframe(time=w.start, scale=scale))
            last_zoom_t = w.start
            # nach ~0.9s leicht zurück
            zooms.append(ZoomKeyframe(time=w.start + 0.85, scale=base_scale + 0.04))

    # Sicherstellen monoton steigender Zeiten
    zooms.sort(key=lambda z: z.time)
    deduped: list[ZoomKeyframe] = []
    for z in zooms:
        if deduped and abs(deduped[-1].time - z.time) < 0.05:
            deduped[-1] = z
        else:
            deduped.append(z)
    return deduped


def zoom_expr(zooms: list[ZoomKeyframe], width: int = 1080, height: int = 1920) -> str:
    """Baut eine ffmpeg zoompan/scale+crop Expression-Kette als Filtergraph-Snippets.

    Wir nutzen scale + crop mit zeitabhängiger Expression (ohne zoompan Frames).
    """
    if not zooms:
        zooms = [ZoomKeyframe(0.0, 1.0)]

    # Piecewise constant scale via nested ifs on t
    # scale(t) = ...
    expr = f"{zooms[-1].scale:.4f}"
    for z in reversed(zooms[:-1]):
        expr = f"if(lt(t\\,{z.time:.3f})\\,{z.scale:.4f}\\,{expr})"

    # Output: wir skalieren das 9:16 Frame um scale und croppen zurück auf width x height
    # Eingangsframe ist bereits 9:16 (out_w x out_h)
    # scale=w* s : h*s, crop=w:h:(in_w-out_w)/2:(in_h-out_h)/2
    filter_str = (
        f"scale=w='{width}*({expr})':h='{height}*({expr})':eval=frame,"
        f"crop={width}:{height}:(in_w-{width})/2:(in_h-{height})/2"
    )
    return filter_str


def even_dimensions(width: int, height: int) -> tuple[int, int]:
    return width - (width % 2), height - (height % 2)
