# Prompt für Codex (fertig zum Einfügen)

Kopiere den Block unten in Codex, zusammen mit dem Repo (oder dem Zip `shorts-maker-codex-handoff.zip`).

---

```text
Du integrierst das Python-Paket `shorts-maker` in meine Social-Media-App.

Lies zuerst verbindlich:
1) CODEX_HANDOFF.md
2) INTEGRATION.md
3) AGENTS.md
4) examples/app_integration.py
5) schemas/pipeline_result.schema.json

Ziel:
- User kann YouTube-URL oder Videoupload geben
- Background-Job erzeugt 9:16 Shorts via:

  from shorts_maker import PipelineOptions, generate_shorts

- Ergebnisse (MP4 + Metadaten) in Object Storage + DB speichern
- Status-API für queued/running/done/failed
- UI: Upload/URL → Progress → Vorschau → Publish

Constraints:
- Nutze die Public API `generate_shorts` (nicht interne Module als App-API)
- Untertitel bleiben 3–5 Wörter
- Pause/Filler-Clean und Zoomcuts bleiben erhalten
- Kein synchrones Rendern im Web-Request (immer Queue/Worker)
- ffmpeg muss verfügbar sein

Definition of Done:
- Endpoint + Worker lauffähig
- Mindestens 1 Short 9:16 im Storage
- Metadaten in DB
- Fehlerfälle (bad URL, kein Speech, ffmpeg missing) sauber behandelt
- Kurze Integrationsnotiz in der App-README
```

---

## Alternativ: Repo an Codex geben

```bash
git clone https://github.com/DerKIProfi/Marius-Lerho.git
cd Marius-Lerho
git fetch origin cursor/codex-handoff-62e4
git checkout cursor/codex-handoff-62e4
```

Oder Zip entpacken und Ordner in Codex öffnen.
