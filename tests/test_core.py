from __future__ import annotations

from pathlib import Path

from shorts_maker.captions import build_ass, chunk_captions
from shorts_maker.clean import clean_transcript
from shorts_maker.download import extract_youtube_id, find_existing_download
from shorts_maker.effects import plan_zoom_cuts
from shorts_maker.models import Word
from shorts_maker.moments import find_moments


def _words(pairs: list[tuple[str, float, float]]) -> list[Word]:
    return [Word(text=t, start=s, end=e) for t, s, e in pairs]


def test_removes_fillers_and_pauses():
    words = _words(
        [
            ("Das", 0.0, 0.2),
            ("ist", 0.25, 0.4),
            ("äh", 0.45, 0.7),
            ("wichtig", 1.8, 2.2),
            ("ähm", 2.3, 2.6),
            ("sofort", 2.7, 3.1),
        ]
    )
    result = clean_transcript(words, max_pause=0.35)
    texts = [w.text for w in result.words]
    assert "äh" not in texts
    assert "ähm" not in texts
    assert texts == ["Das", "ist", "wichtig", "sofort"]
    assert result.removed_fillers == 2
    assert result.removed_pause_seconds > 0.5
    assert result.words[-1].end < words[-1].end


def test_caption_chunks_are_short():
    words = _words(
        [
            ("Das", 0.0, 0.2),
            ("ist", 0.22, 0.35),
            ("ein", 0.37, 0.5),
            ("wirklich", 0.52, 0.9),
            ("wichtiger", 0.92, 1.3),
            ("Tipp", 1.32, 1.6),
            ("für", 1.62, 1.8),
            ("dich", 1.82, 2.1),
            ("heute", 2.12, 2.5),
        ]
    )
    chunks = chunk_captions(words, min_words=3, max_words=5)
    assert chunks
    assert all(2 <= len(c.words) <= 5 for c in chunks)
    assert sum(1 for c in chunks if len(c.words) >= 3) >= len(chunks) - 1
    ass = build_ass(chunks)
    assert "Dialogue:" in ass
    assert any("DAS" in c.text.upper() for c in chunks)


def test_find_moments_are_contiguous():
    # Zwei getrennte Sprechblasen weit auseinander — Short darf nicht quer springen
    words: list[Word] = []
    t = 0.0
    vocab = ["Warum", "das", "wichtig", "ist", "niemand", "kennt", "diesen", "Fehler"]
    for i in range(40):
        words.append(Word(text=vocab[i % len(vocab)], start=t, end=t + 0.3))
        t += 0.4

    # große Lücke
    t = 200.0
    for i in range(40):
        words.append(Word(text=vocab[i % len(vocab)], start=t, end=t + 0.3))
        t += 0.4

    moments = find_moments(
        words,
        max_shorts=2,
        target_duration=20,
        min_duration=12,
        max_duration=30,
        max_gap=2.0,
    )
    assert 1 <= len(moments) <= 2
    for m in moments:
        assert m.duration >= 12
        # Kein Moment darf die 200s-Lücke überspannen
        assert not (m.start < 50 and m.end > 150)
        # Interne Gaps begrenzt
        for i in range(len(m.words) - 1):
            assert m.words[i + 1].start - m.words[i].end <= 2.0 + 1e-6

    zooms = plan_zoom_cuts(moments[0].words)
    assert len(zooms) >= 2
    assert zooms[0].scale >= 1.0


def test_extract_youtube_id():
    assert extract_youtube_id("https://www.youtube.com/watch?v=bxl7nOsZQtc") == "bxl7nOsZQtc"
    assert extract_youtube_id("https://youtu.be/bxl7nOsZQtc") == "bxl7nOsZQtc"
    assert extract_youtube_id("https://www.youtube.com/shorts/abc123XYZ") == "abc123XYZ"
    assert extract_youtube_id("https://example.com/nope") is None


def test_find_existing_download(tmp_path: Path):
    video = tmp_path / "Akustikkonzert [bxl7nOsZQtc].mp4"
    video.write_bytes(b"x" * 1_000_001)
    # Partials must never win over a finished file
    (tmp_path / "bxl7nOsZQtc.f303.webm").write_bytes(b"y" * 2_000_000)
    (tmp_path / "bxl7nOsZQtc.temp.mp4").write_bytes(b"z" * 1_500_000)
    (tmp_path / "partial [bxl7nOsZQtc].mp4").write_bytes(b"tiny")
    found = find_existing_download(
        "https://www.youtube.com/watch?v=bxl7nOsZQtc",
        tmp_path,
    )
    assert found == video.resolve()
    assert find_existing_download("https://www.youtube.com/watch?v=otherid", tmp_path) is None


def test_pick_best_local_video(tmp_path: Path):
    from shorts_maker.download import pick_best_local_video

    good = tmp_path / "Mein_Konzert_bxl7nOsZQtc.mp4"
    good.write_bytes(b"a" * 3_000_000)
    partial = tmp_path / "bxl7nOsZQtc.temp.mp4"
    partial.write_bytes(b"b" * 2_000_000)
    frag = tmp_path / "bxl7nOsZQtc.f251.webm"
    frag.write_bytes(b"c" * 4_000_000)
    chosen = pick_best_local_video([good, partial, frag])
    assert chosen == good.resolve()
