# Shorts Maker

Autonomes Tool/Library: lange **16:9 YouTube-Videos** → interessante **9:16 Shorts** mit

- Entfernung von **Pausen** und **Fülllauten** (äh, ähm, um, …)
- Auswahl spannender Momente (Hook-Heuristik)
- modernen **Zoomcuts** / Punch-Ins
- synchronen **Untertiteln** (typisch **3–5 Wörter** gleichzeitig)

## Übergabe an Codex / App-Integration

Für Marius’ Social-Media-App bitte diese Dateien an Codex übergeben:

| Datei | Zweck |
|-------|--------|
| [`MARIUS_CODEX_PROMPT.md`](MARIUS_CODEX_PROMPT.md) | Fertiger Prompt zum Einfügen in Codex |
| [`CODEX_HANDOFF.md`](CODEX_HANDOFF.md) | Verbindliche Agent-Übergabe |
| [`INTEGRATION.md`](INTEGRATION.md) | Architektur für App-Einbau |
| [`AGENTS.md`](AGENTS.md) | Kurzregeln für Coding Agents |
| [`examples/app_integration.py`](examples/app_integration.py) | Minimaler App-Wrapper |
| [`schemas/pipeline_result.schema.json`](schemas/pipeline_result.schema.json) | Output-Vertrag |

Public API:

```python
from shorts_maker import PipelineOptions, generate_shorts

result = generate_shorts("https://youtube.com/watch?v=…", "output/job1")
print(result.to_dict())
```

## macOS Quickstart

Die Befehle müssen **im geklonten Repo** laufen (nicht im Home-Ordner `~`). Auf dem Mac **`python3`** verwenden.

```bash
git clone https://github.com/DerKIProfi/Marius-Lerho.git
cd Marius-Lerho

brew install ffmpeg
python3 -m pip install -e .

# Offline-Demo (ohne YouTube / ohne Whisper-Download)
python3 scripts/demo_local.py

# Echtes YouTube-Video — Anführungszeichen MÜSSEN geschlossen sein:
python3 -m shorts_maker "https://www.youtube.com/watch?v=DEINE_ID" -o output --model small

# Nach schlechtem Erstlauf: Transkript neu + zusammenhängende Clips
python3 -m shorts_maker "https://www.youtube.com/watch?v=DEINE_ID" -o output \
  --force-transcribe --model small --max-gap 2.0
```

Wenn die Shell `dquote>` zeigt, fehlt ein `"` — mit `Ctrl+C` abbrechen und den Befehl neu eingeben.

### Qualitätshinweise

- Shorts werden aus **zusammenhängenden** Sprechabschnitten gebaut (keine Sprünge quer durchs Video).
- Pausen/Fülllaute werden nur **innerhalb** eines Moments gekürzt.
- `--model small` (Default) oder `medium` verbessert deutsche Untertitel stark gegenüber `base`/`tiny`.
- Altes `output/work/transcript.json` bei Fehlerhaftem Text mit `--force-transcribe` neu erzeugen.

Wenn `pip` / `python3` fehlen:

```bash
xcode-select --install
brew install python
```

## Lokale Videodatei

```bash
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
3. **Clean** – Fülllaute & lange Pausen raus
4. **Moments** – Scoring über Sprechdichte / Hooks
5. **Render** (`ffmpeg`) – 9:16, Zoomcuts, ASS-Untertitel

## Anforderungen

- Python 3.10+ (`python3` auf macOS)
- `ffmpeg` / `ffprobe` im PATH
- optional: GPU für schnellere Whisper-Modelle

### macOS: Untertitel ohne libass/freetype

Viele Homebrew-ffmpeg-Builds auf Intel-Macs haben **weder `ass` noch `drawtext`**.
Das Tool fällt dann automatisch auf **Pillow-PNG-Overlays** zurück und schreibt zusätzlich
`.srt` / `.ass` Sidecar-Dateien neben jedes Short.

Kein `brew reinstall ffmpeg` nötig. Nur:

```bash
python3 -m pip install -e .
python3 -m shorts_maker "https://www.youtube.com/watch?v=DEINE_ID" -o output
```

Wenn die Shell `dquote>` zeigt, fehlt ein schließendes `"` — `Ctrl+C`, Befehl neu eingeben.

## Tests

```bash
python3 -m pip install -e . pytest
python3 -m pytest -q
```
