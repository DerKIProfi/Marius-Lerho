#!/usr/bin/env bash
# Einmalige Einrichtung auf macOS / Linux — Homebrew ist OPTIONAL.
# Nutzung:  bash setup.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Prüfe python3 …"
command -v python3 >/dev/null || {
  echo "FEHLER: python3 fehlt."
  echo "macOS: https://www.python.org/downloads/  (Installer) oder Xcode CLT"
  exit 1
}
python3 --version

echo "==> Installiere Python-Paket (inkl. imageio-ffmpeg = ffmpeg ohne brew) …"
python3 -m pip install -U pip
python3 -m pip install -e .

echo "==> Prüfe ffmpeg …"
if command -v ffmpeg >/dev/null; then
  ffmpeg -version | head -1
else
  echo "Kein System-ffmpeg — nutze gebündeltes imageio-ffmpeg."
  python3 - <<'PY'
from shorts_maker.ffmpeg_bin import ffmpeg_path
print("OK:", ffmpeg_path())
PY
fi

echo "==> Offline-Demo …"
python3 scripts/demo_local.py

echo
echo "Fertig. Nächster Schritt:"
echo "  python3 -m shorts_maker \"https://www.youtube.com/watch?v=VIDEO_ID\" -o output --model small --force-transcribe"
echo "Details: ANLEITUNG_MARIUS.md"
