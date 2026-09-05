# Integration in eine Social-Media-App

Dieses Dokument beschreibt, wie `shorts-maker` als **Media-Processing-Service**
in eine bestehende App eingebettet wird.

## Architektur (empfohlen)

```
App Client
   │  POST /shorts/generate { url | file_id, options }
   ▼
API Gateway / Backend
   │  enqueue job
   ▼
Worker / Queue
   │  shorts_maker.generate_shorts(...)
   ▼
Local work dir → Object Storage (S3/R2/Blob)
   │
   ▼
DB: posts / media_assets / job_status
```

Warum Queue? Whisper + ffmpeg brauchen oft Minuten. Nie synchron im Web-Request rendern.

## Minimaler Python-Worker

```python
from shorts_maker import PipelineOptions, generate_shorts

def handle_job(job):
    result = generate_shorts(
        job["source"],
        output_dir=f"/tmp/shorts/{job['id']}",
        options=PipelineOptions(
            language=job.get("language", "de"),
            model_size=job.get("model_size", "base"),
            max_shorts=job.get("max_shorts", 3),
        ),
    )
    # upload result.shorts[*].file → storage
    # save metadata → db
    return result.to_dict()
```

Vollständigeres Beispiel: `examples/app_integration.py`

## HTTP-API (Vorschlag)

### `POST /api/shorts/generate`

Request:

```json
{
  "source_url": "https://www.youtube.com/watch?v=…",
  "language": "de",
  "max_shorts": 3,
  "target_duration": 35
}
```

oder multipart upload einer Videodatei.

Response:

```json
{ "job_id": "job_123", "status": "queued" }
```

### `GET /api/shorts/jobs/:job_id`

```json
{
  "job_id": "job_123",
  "status": "done",
  "shorts": [
    {
      "asset_url": "https://cdn…/short_01.mp4",
      "title": "…",
      "duration": 28.4,
      "transcript": "…"
    }
  ]
}
```

## Mapping auf App-Domain

| Shorts-Maker Feld | App-Feld (Vorschlag) |
|-------------------|----------------------|
| `shorts[].file` | media asset (mp4), nach Upload CDN-URL |
| `shorts[].title` | Post-Titel / Caption-Vorschlag |
| `shorts[].transcript` | Accessibility / Suche / Chapters |
| `shorts[].duration` | Player-Metadaten |
| `shorts[].score` | Ranking / Auto-Select best clip |
| `aspect 9:16` | `format=short` / Reels-Tab |

## Umgebungsvariablen (Vorschlag)

```bash
SHORTS_WORK_DIR=/var/shorts-work
SHORTS_MODEL_SIZE=base
SHORTS_MAX_SHORTS=3
SHORTS_LANGUAGE=de
FFMPEG_PATH=ffmpeg
```

## Fehlerbehandlung

| Fehler | Ursache | App-Verhalten |
|--------|---------|---------------|
| `FileNotFoundError` | lokale Datei fehlt | 400 |
| yt-dlp Fehler | URL ungültig/blocked | 422 + Upload anbieten |
| `RuntimeError: Keine … Momente` | zu wenig Sprache | 422 |
| `ffmpeg failed` | Codec/Filter/ASS | 500 + Log stderr |
| OOM / timeout | Modell zu groß | Retry mit `tiny`/`base` |

## Sicherheit

- User-Uploads in isoliertem Temp-Dir verarbeiten
- yt-dlp nur gegen allowlistete Hosts (YouTube) oder reiner Upload-Modus
- Worker ohne Secrets der Haupt-DB außer Job-Queue Credentials
- Fertige MP4s auf Virenscan/Größenlimit prüfen bevor Publish

## UI-Flow (kurz)

1. User wählt „Shorts aus Video erstellen“
2. URL oder Upload
3. Progress: Downloading → Transcribing → Cutting → Rendering
4. Vorschau-Carousel der erzeugten Shorts
5. User wählt 1–n Clips → Publish
