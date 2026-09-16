# Shorts Maker — Einrichtung auf Marius’ Rechner

Dieses Paket erzeugt aus langen YouTube-/Videodateien automatisch **9:16 Shorts**
mit Zoomcuts, gekürzten Pausen und synchronen Untertiteln.

**Zielsystem:** macOS (Intel oder Apple Silicon) oder Linux  
**Benötigte Zeit:** ca. 10–20 Minuten Einrichtung, danach pro Video je nach Länge

---

## 1. Was im ZIP steckt

| Ordner / Datei | Zweck |
|----------------|--------|
| `ANLEITUNG_MARIUS.md` | Diese Anleitung (hier starten) |
| `shorts_maker/` | Das Python-Tool |
| `scripts/demo_local.py` | Offline-Test ohne YouTube |
| `examples/` | App-Integrationsbeispiel |
| `CODEX_HANDOFF.md` / `INTEGRATION.md` | Für späteren App-Einbau |
| `requirements.txt` / `pyproject.toml` | Abhängigkeiten |

---

## 2. Voraussetzungen (einmalig)

### 2.1 Speicherplatz

Mindestens **10 GB frei** auf der Systemplatte. Lange Konzertvideos brauchen
oft 1–2 GB Download + Whisper-Modell + Render-Zwischendateien.

```bash
df -h .
```

### 2.2 Python 3.10+

Auf macOS zeigt `python3` oft noch **Apple 3.9.6**, auch wenn neuere Python-Versionen
installiert sind. Prüfen:

```bash
python3 --version
python3.14 --version
python3.12 --version
which -a python3
```

Es muss **≥ 3.10** sein. Wenn `python3` = 3.9.x ist, immer die neue Version nutzen
(z.B. `python3.14` oder `python3.12`).

Falls gar keine neue Version da ist: von https://www.python.org/downloads/ den
macOS-Installer nehmen.
### 2.3 ffmpeg — **Homebrew ist NICHT nötig**

Das Tool bringt ffmpeg über das Python-Paket **`imageio-ffmpeg`** mit.
`brew` brauchst du nicht.

Falls du später trotzdem Homebrew willst (optional):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Danach oft noch PATH setzen (Apple Silicon):

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Hinweis: Viele macOS-ffmpeg-Builds haben **kein** libass/drawtext.
Das Tool fällt dann automatisch auf **Pillow-Untertitel** zurück — das ist OK.

---

## 3. ZIP entpacken und installieren

1. ZIP auf den Rechner kopieren (USB, AirDrop, Download, …).
2. Entpacken, z.B. nach `~/shorts`.
3. Terminal öffnen und:

```bash
cd ~/shorts
python3.14 -m pip install -e .
```

Falls `python3.14` nicht existiert, `python3.12` oder die Version aus `python3.XX --version`
nehmen, die ≥ 3.10 ist — **nicht** das System-`python3` mit 3.9.x.

Optional (empfohlen, separates Environment):

```bash
cd ~/shorts
python3.14 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -e .
```

Bei späteren Terminal-Sitzungen immer wieder:

```bash
cd ~/shorts
source .venv/bin/activate
```

---

## 4. Schnelltest (ohne YouTube)

```bash
cd ~/shorts
python3 scripts/demo_local.py
```

Wenn das durchläuft, ist die Basis-Installation OK.
Ergebnis liegt unter `output/demo/`.

---

## 5. Shorts erzeugen — so führst du es aus

### Variante A: YouTube-Link

```bash
cd ~/shorts
python3 -m shorts_maker "https://www.youtube.com/watch?v=VIDEO_ID" -o output \
  --force-transcribe --model small
```

Wichtig:

- Anführungszeichen um die URL **schließen**
- In zsh **keine** Zeilen mit `# Kommentar` mitkopieren (sonst `command not found: #`)
- Erster Lauf lädt das Whisper-Modell (`small`) herunter — das kann dauern

### Variante B: Lokale Videodatei (empfohlen bei wenig Speicher / Download-Problemen)

```bash
cd ~/shorts
python3 -m shorts_maker "/pfad/zum/video.mp4" -o output \
  --force-transcribe --model small
```

### Nützliche Optionen

| Option | Default | Bedeutung |
|--------|---------|-----------|
| `-o output` | `output` | Ausgabeordner |
| `--model small` | `small` | Whisper-Qualität (`tiny`…`large-v3`) |
| `--language de` | `de` | Sprache |
| `--max-shorts 3` | `3` | Anzahl Shorts |
| `--duration 35` | `35` | Ziellänge in Sekunden |
| `--force-transcribe` | aus | Transkript neu erzeugen |

Beispiel mit weniger Clips:

```bash
python3 -m shorts_maker "https://www.youtube.com/watch?v=VIDEO_ID" -o output \
  --max-shorts 2 --duration 30 --model small --force-transcribe
```

---

## 6. Wo liegen die fertigen Shorts?

```
output/
  shorts/          ← fertige 9:16 MP4s (+ ggf. .srt/.ass)
  work/            ← Download, Transkript, Zwischenstände
  summary.json     ← Übersicht
```

Shorts öffnen z.B. mit QuickTime / VLC:

```bash
open output/shorts
```

---

## 7. Typische Probleme

### „No space left on device“ / Festplatte voll

```bash
df -h .
rm -f output/work/download/*.part output/work/download/*.ytdl
rm -f output/work/download/*.f*.webm output/work/download/*.f*.mp4
rm -f output/work/download/*.temp.mp4
```

Danach lieber **lokale MP4** nutzen (Variante B), nicht nochmal 1 GB von YouTube laden.

### „Postprocessing: Conversion failed!“

ffmpeg konnte Video+Audio nicht mergen. Neuere Versionen des Tools versuchen
mehrere Strategien und nutzen vorhandene Downloads. Workaround:

```bash
python3 -m pip install -U yt-dlp
python3 -m shorts_maker "/pfad/zur/fertigen.mp4" -o output --force-transcribe --model small
```

### Untertitel fehlen / „No such filter: drawtext/ass“

Kein Problem: Tool rendert Untertitel über Pillow und schreibt Sidecar-Dateien.
Kein `brew reinstall ffmpeg` nötig.

### „requires a different Python: 3.9.6 not in '>=3.10'“

Das System-`python3` ist zu alt. Neuere Version verwenden:

```bash
python3.14 --version
cd ~/shorts
python3.14 -m pip install -e .
python3.14 scripts/demo_local.py
```

### „brew: command not found“ / kein ffmpeg

Normal. Homebrew brauchst du nicht. Stattdessen:

```bash
cd ~/shorts
python3.14 -m pip install -e .
python3.14 -c "from shorts_maker.ffmpeg_bin import ffmpeg_path; print(ffmpeg_path())"
```

Wenn das einen Pfad ausgibt, ist ffmpeg über `imageio-ffmpeg` bereit.


### `dquote>` in der Shell

Ein `"` fehlt. Mit `Ctrl+C` abbrechen und den Befehl neu eingeben.

---

## 8. Für die spätere App-Integration

Nicht über CLI erzwingen — Library nutzen:

```python
from shorts_maker import PipelineOptions, generate_shorts

result = generate_shorts(
    "https://www.youtube.com/watch?v=VIDEO_ID",
    "output/job1",
    options=PipelineOptions(language="de", model_size="small", max_shorts=3),
)
print(result.to_dict())
```

Details: `CODEX_HANDOFF.md`, `INTEGRATION.md`, `examples/app_integration.py`.

---

## 9. Checkliste vor dem ersten Echtlauf

- [ ] Python 3.10+ (`python3 --version`)
- [ ] ffmpeg im PATH (`ffmpeg -version`)
- [ ] `python3 -m pip install -e .` erfolgreich
- [ ] `python3 scripts/demo_local.py` erfolgreich
- [ ] ≥ 10 GB frei (`df -h .`)
- [ ] Erster Shorts-Lauf mit kurzem Testvideo oder lokaler Datei
