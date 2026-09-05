#!/usr/bin/env python3
"""Minimalbeispiel: Shorts-Pipeline in einer Social-Media-App einbinden.

In einer echten App würdest du das in einem Background-Job
(Celery, RQ, Inngest, Vercel Workflow, etc.) ausführen.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from shorts_maker import PipelineOptions, generate_shorts


def create_shorts_for_post(
    source_url_or_file: str,
    user_id: str,
    post_id: str,
    *,
    work_root: Path = Path("app_jobs"),
) -> dict:
    """App-ähnlicher Wrapper um generate_shorts()."""
    output_dir = work_root / user_id / post_id
    options = PipelineOptions(
        language="de",
        model_size="base",
        max_shorts=3,
        target_duration=35.0,
        width=1080,
        height=1920,
    )
    result = generate_shorts(source_url_or_file, output_dir, options)

    # So könnte die App die Clips in ihrer DB speichern:
    assets = []
    for clip in result.shorts:
        assets.append(
            {
                "type": "short",
                "path": clip.file,
                "title": clip.title,
                "duration": clip.duration,
                "score": clip.score,
                "transcript": clip.transcript,
                "aspect_ratio": "9:16",
            }
        )

    payload = {
        "user_id": user_id,
        "post_id": post_id,
        "source": result.source,
        "removed_fillers": result.removed_fillers,
        "removed_pause_seconds": result.removed_pause_seconds,
        "assets": assets,
        "summary_path": result.summary_path,
    }
    (output_dir / "app_payload.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python examples/app_integration.py <youtube-url-or-local-file>")
        print("Tipp: python scripts/demo_local.py  # erzeugt lokal Demo-Shorts")
        raise SystemExit(2)

    payload = create_shorts_for_post(
        sys.argv[1],
        user_id="demo-user",
        post_id="demo-post-001",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
