#!/usr/bin/env bash
# Einmalige Einrichtung auf macOS / Linux.
# Nutzung:  bash setup.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Prüfe python3 …"
command -v python3 >/dev/null || { echo "FEHLER: python3 fehlt. macOS: brew install python"; exit 1; }
python3 --version

echo "==> Prüfe ffmpeg …"
if ! command -v ffmpeg >/dev/null; then
  echo "WARNUNG: ffmpeg fehlt."
  if command -v brew >/dev/null; then
    echo "Installiere ffmpeg mit Homebrew …"
    brew install ffmpeg
  else
    echo "Bitte ffmpeg manuell installieren (brew install ffmpeg / apt install ffmpeg)."
    exit 1
  fi
fi
ffmpeg -version | head -1

echo "==> Installiere Python-Paket (editable) …"
python3 -m pip install -U pip
python3 -m pip install -e .

echo "==> Offline-Demo …"
python3 scripts/demo_local.py

echo
echo "Fertig. Nächster Schritt:"
echo "  python3 -m shorts_maker \"https://www.youtube.com/watch?v=VIDEO_ID\" -o output --model small --force-transcribe"
echo "Details: ANLEITUNG_MARIUS.md"
