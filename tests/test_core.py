from __future__ import annotations

from shorts_maker.captions import build_ass, chunk_captions
from shorts_maker.clean import clean_transcript
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
            ("wichtig", 1.8, 2.2),  # lange Pause davor
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
    # bereinigte Timeline kompakter
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


def test_find_moments_and_zooms():
    # ~40s synthetischer Monolog
    words: list[Word] = []
    t = 0.0
    vocab = [
        "Warum",
        "das",
        "wichtig",
        "ist",
        "niemand",
        "kennt",
        "diesen",
        "Fehler",
        "Du",
        "musst",
        "sofort",
        "handeln",
        "und",
        "nie",
        "wieder",
        "warten",
    ]
    for i in range(80):
        text = vocab[i % len(vocab)]
        words.append(Word(text=text, start=t, end=t + 0.28))
        t += 0.35 + (0.8 if i % 10 == 9 else 0.0)

    cleaned = clean_transcript(words, max_pause=0.4)
    moments = find_moments(cleaned.words, max_shorts=2, target_duration=20, min_duration=12, max_duration=30)
    assert 1 <= len(moments) <= 2
    assert all(m.duration >= 12 for m in moments)

    zooms = plan_zoom_cuts(moments[0].words)
    assert len(zooms) >= 2
    assert zooms[0].scale >= 1.0
