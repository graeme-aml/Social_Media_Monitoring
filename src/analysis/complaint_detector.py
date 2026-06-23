import re
from typing import Optional

import anthropic

from src.models import Post, Complaint, Severity


KEYWORD_SEVERITY: dict[str, Severity] = {
    # High severity
    "scam": Severity.HIGH,
    "fraud": Severity.HIGH,
    "lawsuit": Severity.HIGH,
    "legal action": Severity.HIGH,
    "reporting you": Severity.HIGH,
    "trading standards": Severity.HIGH,
    "bbb complaint": Severity.HIGH,
    # Medium severity
    "refund": Severity.MEDIUM,
    "terrible": Severity.MEDIUM,
    "awful": Severity.MEDIUM,
    "unacceptable": Severity.MEDIUM,
    "never again": Severity.MEDIUM,
    "worst": Severity.MEDIUM,
    "disgusting": Severity.MEDIUM,
    # Low severity
    "broken": Severity.LOW,
    "not working": Severity.LOW,
    "problem": Severity.LOW,
    "issue": Severity.LOW,
    "disappointed": Severity.LOW,
    "complaint": Severity.LOW,
    "fix this": Severity.LOW,
    "customer service": Severity.LOW,
}


class ComplaintDetector:
    def __init__(self, anthropic_client: Optional[anthropic.Anthropic], min_confidence: float = 0.6):
        self.anthropic_client = anthropic_client
        self.min_confidence = min_confidence

    def analyze(self, post: Post, extra_keywords: list[str]) -> Optional[Complaint]:
        matched = self._keyword_match(post.text, extra_keywords)
        if not matched and not self._looks_like_complaint(post.text):
            return None

        if self.anthropic_client:
            return self._ai_analyze(post, matched)
        return self._heuristic_analyze(post, matched)

    def _keyword_match(self, text: str, extra_keywords: list[str]) -> list[str]:
        lower = text.lower()
        all_keywords = {**KEYWORD_SEVERITY, **{k.lower(): Severity.LOW for k in extra_keywords}}
        return [kw for kw in all_keywords if kw in lower]

    def _looks_like_complaint(self, text: str) -> bool:
        patterns = [
            r"\bwhy (is|are|won't|can't|doesn't|didn't)\b",
            r"\bstill (waiting|broken|not working)\b",
            r"\b(no|zero) (response|reply|help|support)\b",
            r"\b(hours|days|weeks) (and|later|still)\b",
        ]
        lower = text.lower()
        return any(re.search(p, lower) for p in patterns)

    def _heuristic_analyze(self, post: Post, matched: list[str]) -> Optional[Complaint]:
        if not matched:
            return None

        severity = max(
            (KEYWORD_SEVERITY.get(kw, Severity.LOW) for kw in matched),
            key=lambda s: [Severity.LOW, Severity.MEDIUM, Severity.HIGH].index(s),
            default=Severity.LOW,
        )
        confidence = min(0.5 + len(matched) * 0.1, 0.9)

        if confidence < self.min_confidence:
            return None

        return Complaint(
            post=post,
            is_complaint=True,
            confidence=round(confidence, 2),
            severity=severity,
            matched_keywords=matched,
            summary=f"Potential complaint mentioning: {', '.join(matched)}",
            analysis="Heuristic match — no AI analysis available (ANTHROPIC_API_KEY not set).",
        )

    def _ai_analyze(self, post: Post, matched_keywords: list[str]) -> Optional[Complaint]:
        prompt = f"""Analyse this social media post and determine if it is a genuine customer complaint.

Post platform: {post.platform.value}
Author: @{post.author}
Text: {post.text}
Matched complaint keywords: {', '.join(matched_keywords) if matched_keywords else 'none'}

Respond with a JSON object containing:
- is_complaint (boolean): true if this is a genuine complaint
- confidence (float 0-1): how confident you are
- severity (string): "low", "medium", or "high"
- summary (string): one sentence summary of the complaint
- analysis (string): 2-3 sentence explanation of your reasoning

Only output valid JSON, no other text."""

        response = self.anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )

        import json
        try:
            data = json.loads(response.content[0].text)
        except (json.JSONDecodeError, IndexError, KeyError):
            return self._heuristic_analyze(post, matched_keywords)

        if not data.get("is_complaint"):
            return None

        confidence = float(data.get("confidence", 0.5))
        if confidence < self.min_confidence:
            return None

        return Complaint(
            post=post,
            is_complaint=True,
            confidence=round(confidence, 2),
            severity=Severity(data.get("severity", "low")),
            matched_keywords=matched_keywords,
            summary=data.get("summary", ""),
            analysis=data.get("analysis", ""),
        )
