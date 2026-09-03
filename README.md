# Shorts Maker

Autonomes CLI-Tool: lange **16:9 YouTube-Videos** → interessante **9:16 Shorts** mit

- Entfernung von **Pausen** und **Fülllauten** (äh, ähm, um, …)
- Auswahl spannender Momente (Hook-Heuristik)
- modernen **Zoomcuts** / Punch-Ins
- synchronen **Untertiteln** (typisch **3–5 Wörter** gleichzeitig)

## Quickstart

```bash
python3 -m pip install -e .
python3 -m shorts_maker "https://www.youtube.com/watch?v=VIDEO_ID" -o output
```

Oder mit lokaler Datei:

```bash
python3 -m shorts_maker /pfad/zum/video.mp4 -o output --language de --model base
```

Ergebnis:

```
output/
  work/           # Download, Transkript, Keep-Ranges
  shorts/         # fertige 9:16 MP4s + Metadaten
  summary.json
```

## Wichtige Optionen

| Option | Default | Bedeutung |
|--------|---------|-----------|
| `--max-shorts` | 3 | Anzahl erzeugter Clips |
| `--duration` | 35 | Ziel-Länge (Sekunden) |
| `--max-pause` | 0.35 | Pausen länger als das werden rausgeschnitten |
| `--model` | base | Whisper-Größe (`tiny` … `large-v3`) |
| `--language` | de | Sprache (`auto` für Erkennung) |

## Pipeline

1. **Download** (`yt-dlp`)
2. **Transkription** (`faster-whisper`, Word-Timestamps + VAD)
3. **Clean** – Fülllaute & lange Pausen raus, kompakte Timeline
4. **Moments** – Scoring über Sprechdichte, Hooks (`warum`, `fehler`, `!`, …)
5. **Render** (`ffmpeg`) – Center-Crop 9:16, Zoomcuts, ASS-Untertitel einbrennen

## Anforderungen

- Python 3.10+
- `ffmpeg` / `ffprobe` im PATH
- optional: GPU für schnellere Whisper-Modelle

## Tests

```bash
python3 -m pip install -e ".[dev]" 2>/dev/null || python3 -m pip install -e . pytest
pytest -q
```
