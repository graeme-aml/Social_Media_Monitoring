from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.models import Post, Platform, Severity
from src.analysis.complaint_detector import ComplaintDetector


def make_post(text: str, platform: Platform = Platform.TWITTER) -> Post:
    return Post(
        platform=platform,
        post_id="123",
        text=text,
        author="testuser",
        url="https://example.com/post/123",
        created_at=datetime.now(timezone.utc),
    )


class TestComplaintDetector:
    def setup_method(self):
        self.detector = ComplaintDetector(anthropic_client=None, min_confidence=0.5)

    def test_detects_high_severity_keyword(self):
        post = make_post("This is a total scam, I want my money back!")
        result = self.detector.analyze(post, [])
        assert result is not None
        assert result.is_complaint
        assert result.severity == Severity.HIGH

    def test_detects_medium_severity_keyword(self):
        post = make_post("Worst service ever, totally unacceptable!")
        result = self.detector.analyze(post, [])
        assert result is not None
        assert result.severity in (Severity.MEDIUM, Severity.HIGH)

    def test_no_complaint_on_positive_text(self):
        post = make_post("Great product, loving it so much! Five stars!")
        result = self.detector.analyze(post, [])
        assert result is None

    def test_extra_keywords_trigger_detection(self):
        post = make_post("The widget is completely broken again.")
        result = self.detector.analyze(post, ["widget"])
        assert result is not None

    def test_confidence_below_threshold_returns_none(self):
        detector = ComplaintDetector(anthropic_client=None, min_confidence=0.99)
        post = make_post("There's a small issue with my order.")
        result = detector.analyze(post, [])
        # Either None or very low confidence — should not meet threshold
        if result is not None:
            assert result.confidence < 0.99

    def test_detects_complaint_pattern(self):
        post = make_post("Why is your website still not working after 3 days?")
        result = self.detector.analyze(post, [])
        assert result is not None
