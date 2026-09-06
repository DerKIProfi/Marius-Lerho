from __future__ import annotations

from shorts_maker.api import PipelineOptions, PipelineResult, ShortClip, generate_shorts


def test_short_clip_from_dict():
    clip = ShortClip.from_dict(
        {
            "file": "/tmp/a.mp4",
            "title": "Test",
            "score": 1.5,
            "duration": 12.0,
            "start": 0.0,
            "end": 12.0,
            "captions": 3,
            "zooms": 2,
            "transcript": "Hallo Welt",
        }
    )
    assert clip.file.endswith("a.mp4")
    assert clip.title == "Test"
    assert clip.transcript == "Hallo Welt"


def test_pipeline_result_to_dict():
    result = PipelineResult(
        source="/tmp/src.mp4",
        removed_fillers=2,
        removed_pause_seconds=1.25,
        shorts=[],
        summary_path="/tmp/summary.json",
        output_dir="/tmp/out",
    )
    data = result.to_dict()
    assert data["removed_fillers"] == 2
    assert data["output_dir"] == "/tmp/out"
    assert data["shorts"] == []


def test_pipeline_options_defaults():
    opts = PipelineOptions()
    assert opts.language == "de"
    assert opts.width == 1080
    assert opts.height == 1920
    assert generate_shorts.__name__ == "generate_shorts"
