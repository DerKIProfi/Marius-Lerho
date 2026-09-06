# AGENTS.md

Dieses Repo enthält **shorts-maker**, ein Python-Tool/Library zum Erzeugen von 9:16 Shorts.

## Für Codex / Coding Agents

1. Lies zuerst **`CODEX_HANDOFF.md`** (verbindliche Übergabe).
2. Lies **`INTEGRATION.md`** für App-Architektur (Queue, API, Storage).
3. Nutze die Public API:

```python
from shorts_maker import generate_shorts, PipelineOptions
```

4. Beispiel-Integration: `examples/app_integration.py`
5. Output-Schema: `schemas/pipeline_result.schema.json`
6. Tests: `python3 -m pytest -q`
7. Offline-Demo: `python3 scripts/demo_local.py`

## Nicht tun

- CLI als einzige Integrationsmethode erzwingen (Library-API bevorzugen)
- Untertitel-Chunking auf lange Sätze umstellen
- ffmpeg-Abhängigkeit entfernen ohne Ersatz
- Synchron im Web-Request rendern (immer Background-Job)

## Stack

Python 3.10+, ffmpeg, yt-dlp, faster-whisper.
