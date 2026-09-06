# CODEX HANDOFF — Shorts Maker → Social Media App

> **Für Marius / Codex:** Dieses Dokument ist die verbindliche Übergabe.
> Ziel: `shorts_maker` in eine eigene Social-Media-App integrieren
> (Upload → Shorts erzeugen → in Feed/Posts speichern).

## 1. Was dieses Projekt ist

Python-Paket **`shorts-maker`**, das aus langen 16:9-Videos (YouTube-URL oder lokale Datei) automatisch **9:16 Shorts** erzeugt:

1. Download (`yt-dlp`)
2. Transkription mit Word-Timestamps (`faster-whisper`)
3. Entfernen von Fülllauten (`äh`, `ähm`, `um`, …) und langen Pausen
4. Auswahl spannender Momente (Hook-Heuristik)
5. Render mit **Zoomcuts** + synchronen Untertiteln (**3–5 Wörter**)

## 2. Empfohlener Einstiegspunkt (nicht umgehen)

```python
from shorts_maker import PipelineOptions, generate_shorts

result = generate_shorts(
    "https://www.youtube.com/watch?v=VIDEO_ID",  # oder /path/to/video.mp4
    output_dir="jobs/user123/post456",
    options=PipelineOptions(
        language="de",
        model_size="base",
        max_shorts=3,
        target_duration=35.0,
        width=1080,
        height=1920,
    ),
)

for clip in result.shorts:
    print(clip.file, clip.title, clip.duration, clip.transcript)
```

**Interna** (`clean.py`, `render.py`, ffmpeg-Filter) nur ändern, wenn nötig.
App-Code sollte über `shorts_maker.api` / `generate_shorts` gehen.

Siehe auch: `examples/app_integration.py`, `INTEGRATION.md`.

## 3. Repo-Layout

```
shorts_maker/
  api.py           # Public API (generate_shorts) ← App-Einstieg
  pipeline.py      # Orchestrierung
  download.py      # yt-dlp
  transcribe.py    # Whisper word timestamps
  clean.py         # Filler + Pause removal
  moments.py       # Hook scoring / Momentwahl
  captions.py      # 3–5 Wort Chunks + ASS
  effects.py       # Zoomcut keyframes
  render.py        # ffmpeg 9:16 render
  models.py        # Dataclasses
  cli.py           # CLI
examples/
  app_integration.py
scripts/
  demo_local.py    # Offline-Demo ohne YouTube/Whisper
tests/
schemas/
  pipeline_result.schema.json
CODEX_HANDOFF.md   # dieses File
INTEGRATION.md
AGENTS.md
```

## 4. System-Abhängigkeiten

| Dependency | Pflicht | Hinweis |
|------------|---------|---------|
| Python 3.10+ | ja | auf macOS: `python3` |
| ffmpeg + ffprobe | ja | `brew install ffmpeg` / apt |
| yt-dlp | ja (pip) | YouTube-Download |
| faster-whisper | ja (pip) | CPU ok (`int8`), GPU optional |
| click, tqdm | ja (pip) | CLI / Progress |

Install:

```bash
git clone https://github.com/DerKIProfi/Marius-Lerho.git
cd Marius-Lerho
git checkout cursor/codex-handoff-62e4   # oder main, sobald gemerged
python3 -m pip install -e .
# ffmpeg muss im PATH sein
```

Offline-Smoke-Test:

```bash
python3 scripts/demo_local.py
python3 -m pytest -q
```

## 5. Output-Vertrag (für DB / Storage)

Nach `generate_shorts(...)` liegt unter `output_dir`:

```
output_dir/
  work/
    download/…
    transcript.json
    transcript_clean.json
    keep_ranges.json
  shorts/
    short_01_….mp4
    short_01.json
  summary.json
```

`PipelineResult.to_dict()` Shape:

```json
{
  "source": "/abs/path/to/source.mp4",
  "removed_fillers": 12,
  "removed_pause_seconds": 34.5,
  "shorts": [
    {
      "file": "/abs/path/shorts/short_01_….mp4",
      "title": "Warum das niemand weiß",
      "score": 8.2,
      "duration": 28.4,
      "start": 12.0,
      "end": 40.4,
      "captions": 14,
      "zooms": 9,
      "transcript": "…"
    }
  ],
  "summary_path": "…/summary.json",
  "output_dir": "…"
}
```

Schema: `schemas/pipeline_result.schema.json`

## 6. Integrationsauftrag an Codex (konkret)

Baue in Marius’ Social-Media-App:

1. **Job/Endpoint** `POST /api/shorts/generate`
   - Input: `source_url` oder Upload-File-ID, `user_id`, optionale Settings
   - Startet Background-Job (nicht request-thread-blockierend)
2. **Worker** ruft `generate_shorts(...)` auf
3. **Nach Erfolg**
   - MP4s nach Object Storage hochladen
   - DB-Records für Post/Assets anlegen (`aspect_ratio=9:16`)
4. **Status-API** `GET /api/shorts/jobs/:id` → `queued|running|done|failed`
5. **UI**: Upload/URL → Progress → Vorschau → Publish

Nicht kaputtmachen:

- Untertitel 3–5 Wörter
- Pause/Filler-Clean
- 9:16 Output
- Public API `generate_shorts` als Fassade

## 7. Performance-Hinweise

- `model_size="tiny"|"base"` für CPU; `small+` nur mit genug RAM/GPU
- Queue + Timeouts + Retries verwenden
- `work/` nach Upload der Shorts löschen
- YouTube-Download kann failen → Upload-Pfad als Fallback

## 8. Bekannte Grenzen (v1)

- Center-Crop (noch kein Face-Tracking)
- Momentwahl heuristisch (kein LLM)
- Untertitel eingebrannt (nicht Soft-Subs)
- Kein Multi-Speaker-Diarization

Next Steps:

- Face-aware Crop
- LLM-Hook-Auswahl / Titel
- Branding-Templates
- Webhook bei Job-Done

## 9. Quick Commands

```bash
python3 -m shorts_maker "URL" -o output --language de --model base --max-shorts 3
python3 examples/app_integration.py /path/to/video.mp4
python3 -m pytest -q
```

## 10. Definition of Done

- [ ] `shorts_maker` als Dependency installierbar
- [ ] Background-Job erzeugt ≥1 MP4 9:16
- [ ] Metadaten in DB gespeichert
- [ ] Dateien in App-Storage
- [ ] Fehlerfälle sauber surfaced
- [ ] E2E- oder Demo-Flow dokumentiert
