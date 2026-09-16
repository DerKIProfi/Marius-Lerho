#!/usr/bin/env bash
# Einmalige Einrichtung auf macOS / Linux — Homebrew ist OPTIONAL.
# Erstellt automatisch eine venv (nötig wegen PEP 668 / externally-managed).
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
  exit 1
fi
echo "Nutze: $PY ($($PY --version 2>&1))"

if [[ ! -d .venv ]]; then
  echo "==> Erzeuge virtuelle Umgebung .venv …"
  "$PY" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
echo "Aktiviert: $(python --version 2>&1) @ $(command -v python)"

echo "==> Installiere Python-Paket …"
python -m pip install -U pip
python -m pip install -e .

echo "==> Prüfe ffmpeg …"
if command -v ffmpeg >/dev/null; then
  ffmpeg -version | head -1
else
  echo "Kein System-ffmpeg — nutze gebündeltes imageio-ffmpeg."
  python - <<'PY'
from shorts_maker.ffmpeg_bin import ffmpeg_path
print("OK:", ffmpeg_path())
PY
fi

echo "==> Offline-Demo …"
python scripts/demo_local.py

echo
echo "Fertig. Vor jedem Lauf die venv aktivieren:"
echo "  cd ~/shorts"
echo "  source .venv/bin/activate"
echo "  python -m shorts_maker \"https://www.youtube.com/watch?v=VIDEO_ID\" -o output --model small --force-transcribe"
echo "Details: ANLEITUNG_MARIUS.md"
