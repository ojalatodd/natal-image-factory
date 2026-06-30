"""Regression tests for segment_text() no-audio and fallback paths."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("BOOTSTRAP_USER_EMAIL", "")
os.environ.setdefault("BOOTSTRAP_USER_PASSWORD", "")

from app.ai import segment_text, _fallback_segment


def test_fallback_segment_basic():
    """_fallback_segment produces a valid single-segment dict."""
    seg = _fallback_segment("Some article text", 45.0)
    assert seg["index"] == 1
    assert seg["start_s"] == 0.0
    assert seg["end_s"] == 45.0
    assert seg["duration_s"] == 45.0
    assert seg["theme_label"] == "Full narration"
    assert "Some article text" in seg["summary"]
    assert seg["search_query"] == "historical illustration"


def test_fallback_segment_empty_text():
    """_fallback_segment handles empty article text gracefully."""
    seg = _fallback_segment("", 30.0)
    assert seg["summary"] == ""
    assert seg["duration_s"] == 30.0


def test_segment_text_no_audio_no_ai_returns_default_segment():
    """When there's no audio and no AI response, segment_text returns
    a single fallback segment with target_segment_s duration."""
    transcript = {"duration_s": 0.0, "words": []}
    # Pass a config that will fail _chat_json (no provider/key)
    segments = segment_text("Some article", transcript, ai_config=None, target_segment_s=30.0)
    assert len(segments) == 1
    assert segments[0]["duration_s"] == 30.0
    assert segments[0]["start_s"] == 0.0
    assert segments[0]["end_s"] == 30.0


def test_segment_text_no_audio_uses_target_segment_s():
    """No-audio mode should use target_segment_s, not 0."""
    transcript = {"duration_s": 0.0, "words": []}
    segments = segment_text("Test", transcript, ai_config=None, target_segment_s=15.0)
    assert len(segments) == 1
    assert segments[0]["duration_s"] == 15.0


def test_segment_text_with_audio_duration_uses_it():
    """When audio duration is present but AI fails, fallback uses audio duration."""
    transcript = {"duration_s": 120.0, "words": []}
    segments = segment_text("Test", transcript, ai_config=None, target_segment_s=30.0)
    assert len(segments) == 1
    assert segments[0]["duration_s"] == 120.0
    assert segments[0]["end_s"] == 120.0
