#!/usr/bin/env bash
# Einmalige Einrichtung auf macOS / Linux — Homebrew ist OPTIONAL.
# Nutzung:  bash setup.sh
set -euo pipefail
cd "$(dirname "$0")"

pick_python() {
  local c
  for c in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1; then
      if "$c" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
        echo "$c"
        return 0
      fi
    fi
  done
  return 1
}

echo "==> Suche Python >= 3.10 …"
if ! PY="$(pick_python)"; then
  echo "FEHLER: Kein Python >= 3.10 gefunden."
  echo "macOS: https://www.python.org/downloads/  (Installer)"
  echo "Danach z.B.: python3.14 -m pip install -e ."
  exit 1
fi
echo "Nutze: $PY ($($PY --version 2>&1))"

echo "==> Installiere Python-Paket (inkl. imageio-ffmpeg = ffmpeg ohne brew) …"
"$PY" -m pip install -U pip
"$PY" -m pip install -e .

echo "==> Prüfe ffmpeg …"
if command -v ffmpeg >/dev/null; then
  ffmpeg -version | head -1
else
  echo "Kein System-ffmpeg — nutze gebündeltes imageio-ffmpeg."
  "$PY" - <<'PY'
from shorts_maker.ffmpeg_bin import ffmpeg_path
print("OK:", ffmpeg_path())
PY
fi

echo "==> Offline-Demo …"
"$PY" scripts/demo_local.py

echo
echo "Fertig. Immer dieselbe Python-Version nutzen, z.B.:"
echo "  $PY -m shorts_maker \"https://www.youtube.com/watch?v=VIDEO_ID\" -o output --model small --force-transcribe"
echo "Details: ANLEITUNG_MARIUS.md"
