# Shorts Maker

Autonomes CLI-Tool: lange **16:9 YouTube-Videos** → interessante **9:16 Shorts** mit

- Entfernung von **Pausen** und **Fülllauten** (äh, ähm, um, …)
- Auswahl spannender Momente (Hook-Heuristik)
- modernen **Zoomcuts** / Punch-Ins
- synchronen **Untertiteln** (typisch **3–5 Wörter** gleichzeitig)

## macOS Quickstart

Die Befehle müssen **im geklonten Repo** laufen (nicht im Home-Ordner `~`). Auf dem Mac bitte **`python3`** verwenden.

```bash
# 1) Repo holen und hineinwechseln
git clone https://github.com/DerKIProfi/Marius-Lerho.git
cd Marius-Lerho

# Optional: PR-Branch mit dem Tool
git fetch origin cursor/youtube-shorts-tool-62e4
git checkout cursor/youtube-shorts-tool-62e4

# 2) Abhängigkeiten (ffmpeg + Python-Paket)
brew install ffmpeg
python3 -m pip install -e .

# 3a) Offline-Demo (ohne YouTube / ohne Whisper-Download)
python3 scripts/demo_local.py

# 3b) Echtes YouTube-Video (VIDEO_ID durch echte ID ersetzen)
python3 -m shorts_maker "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -o output
```

Wenn `pip` / `python3` fehlen:

```bash
xcode-select --install
brew install python
```

## Lokale Videodatei

```bash
cd Marius-Lerho
python3 -m shorts_maker /pfad/zum/video.mp4 -o output --language de --model base
```

## Ergebnis

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

- Python 3.10+ (`python3` auf macOS)
- `ffmpeg` / `ffprobe` im PATH (`brew install ffmpeg`)
- optional: GPU für schnellere Whisper-Modelle

## Tests

```bash
python3 -m pip install -e . pytest
python3 -m pytest -q
```
