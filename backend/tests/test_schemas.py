"""Unit tests for ProjectSettings.visual_style validator (issue #10)."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("BOOTSTRAP_USER_EMAIL", "")
os.environ.setdefault("BOOTSTRAP_USER_PASSWORD", "")

import pytest
from pydantic import ValidationError

from app.schemas import ProjectSettings


class TestVisualStyleValidator:
    def test_valid_style_classical(self):
        s = ProjectSettings(visual_style="classical_antiquity")
        assert s.visual_style == "classical_antiquity"

    def test_valid_style_medieval(self):
        s = ProjectSettings(visual_style="medieval")
        assert s.visual_style == "medieval"

    def test_valid_style_renaissance(self):
        s = ProjectSettings(visual_style="renaissance")
        assert s.visual_style == "renaissance"

    def test_valid_style_modern(self):
        s = ProjectSettings(visual_style="modern")
        assert s.visual_style == "modern"

    def test_valid_style_ai_judgement(self):
        s = ProjectSettings(visual_style="ai_judgement")
        assert s.visual_style == "ai_judgement"

    def test_none_passes(self):
        s = ProjectSettings(visual_style=None)
        assert s.visual_style is None

    def test_omitted_passes(self):
        s = ProjectSettings()
        assert s.visual_style is None

    def test_invalid_style_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            ProjectSettings(visual_style="nonexistent_style")
        assert "Invalid visual style preset" in str(exc_info.value)

    def test_empty_string_raises(self):
        with pytest.raises(ValidationError):
            ProjectSettings(visual_style="")

    def test_other_fields_unaffected(self):
        s = ProjectSettings(visual_style="modern", ai_images_enabled=True, ai_video_motion=True)
        assert s.visual_style == "modern"
        assert s.ai_images_enabled is True
        assert s.ai_video_motion is True
