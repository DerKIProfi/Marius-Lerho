from __future__ import annotations

from pathlib import Path

from shorts_maker.models import CaptionChunk, Word


def chunk_captions(
    words: list[Word],
    *,
    min_words: int = 3,
    max_words: int = 5,
    max_chars: int = 22,
    max_gap: float = 0.55,
) -> list[CaptionChunk]:
    """Gruppiert Wörter zu kurzen, synchrone Caption-Chunks (3–5 Wörter)."""
    if not words:
        return []

    chunks: list[CaptionChunk] = []
    current: list[Word] = []

    def flush() -> None:
        nonlocal current
        if not current:
            return
        chunks.append(
            CaptionChunk(
                words=list(current),
                start=current[0].start,
                end=max(current[-1].end, current[0].start + 0.35),
            )
        )
        current = []

    for w in words:
        if not current:
            current = [w]
            continue

        gap = w.start - current[-1].end
        text_len = sum(len(x.text) for x in current) + len(w.text) + len(current)
        would_exceed = len(current) >= max_words or text_len > max_chars
        soft_break = len(current) >= min_words and (
            gap > max_gap
            or current[-1].text.rstrip().endswith((".", "!", "?", ",", ";", ":"))
            or text_len >= max_chars - 4
        )

        if would_exceed or soft_break:
            flush()
            current = [w]
        else:
            current.append(w)

    flush()

    # Zu kurze Rest-Chunks an Vorgänger oder Nachfolger hängen
    merged: list[CaptionChunk] = []
    for chunk in chunks:
        if merged and len(chunk.words) < min_words:
            prev = merged[-1]
            combined = prev.words + chunk.words
            combined_len = sum(len(w.text) for w in combined) + max(0, len(combined) - 1)
            if len(combined) <= max_words and combined_len <= max_chars:
                merged[-1] = CaptionChunk(words=combined, start=prev.start, end=chunk.end)
                continue
        merged.append(chunk)

    # Noch kurze Chunks nach vorne in den nächsten schieben
    final: list[CaptionChunk] = []
    i = 0
    while i < len(merged):
        chunk = merged[i]
        if len(chunk.words) < min_words and i + 1 < len(merged):
            nxt = merged[i + 1]
            combined = chunk.words + nxt.words
            combined_len = sum(len(w.text) for w in combined) + max(0, len(combined) - 1)
            if len(combined) <= max_words and combined_len <= max_chars + 2:
                final.append(CaptionChunk(words=combined, start=chunk.start, end=nxt.end))
                i += 2
                continue
        final.append(chunk)
        i += 1
    chunks = final

    # Überlappungen vermeiden / minimale Lesbarkeit
    for i in range(len(chunks) - 1):
        if chunks[i].end > chunks[i + 1].start:
            mid = (chunks[i].end + chunks[i + 1].start) / 2
            chunks[i].end = mid
            chunks[i + 1].start = mid

    return chunks


def _ass_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 0
        s += 1
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def build_ass(
    captions: list[CaptionChunk],
    *,
    play_res_x: int = 1080,
    play_res_y: int = 1920,
    font_name: str = "DejaVu Sans",
    font_size: int | None = None,
    primary_color: str = "&H00FFFFFF",
    outline_color: str = "&H00000000",
    margin_v: int | None = None,
) -> str:
    """Erzeugt ASS-Untertitel im modernen Shorts-Stil (groß, zentriert, Outline)."""
    if font_size is None:
        # Konservativ, damit 3–5 Wörter auf einer Zeile Platz haben
        font_size = max(36, min(56, int(play_res_x * 0.048)))
    if margin_v is None:
        margin_v = int(play_res_y * 0.28)

    header = f"""[Script Info]
Title: Shorts Captions
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},&H000000FF,{outline_color},&H80000000,-1,0,0,0,100,100,0,0,1,5,0,2,80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for chunk in captions:
        text = chunk.text.upper().replace("\n", " ")
        text = text.replace("{", "(").replace("}", ")")
        # Leichter Pop + sichere Breite
        animated = (
            r"{\an2\fad(80,60)\fscx102\fscy102\t(0,120,\fscx100\fscy100)\bord5\shad0}"
            + text
        )
        lines.append(
            f"Dialogue: 0,{_ass_time(chunk.start)},{_ass_time(chunk.end)},Default,,0,0,0,,{animated}"
        )
    return "\n".join(lines) + "\n"


def write_ass(path, captions: list[CaptionChunk], **kwargs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_ass(captions, **kwargs), encoding="utf-8")


def _srt_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        ms = 0
        s += 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(captions: list[CaptionChunk]) -> str:
    lines: list[str] = []
    for i, chunk in enumerate(captions, start=1):
        lines.append(str(i))
        lines.append(f"{_srt_time(chunk.start)} --> {_srt_time(chunk.end)}")
        lines.append(chunk.text.upper())
        lines.append("")
    return "\n".join(lines)


def write_srt(path, captions: list[CaptionChunk]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_srt(captions), encoding="utf-8")
