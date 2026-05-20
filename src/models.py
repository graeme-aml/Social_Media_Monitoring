from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Platform(str, Enum):
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    BLUESKY = "bluesky"
    TIKTOK = "tiktok"
    TWITCH = "twitch"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Post(BaseModel):
    platform: Platform
    post_id: str
    text: str
    author: str
    url: str
    created_at: datetime
    raw: dict[str, Any] = Field(default_factory=dict)


class Complaint(BaseModel):
    post: Post
    is_complaint: bool
    confidence: float  # 0.0 – 1.0
    severity: Severity
    matched_keywords: list[str]
    summary: str  # one-line AI summary
    analysis: str  # full AI analysis


class MonitoringReport(BaseModel):
    run_at: datetime
    platforms_scraped: list[Platform]
    total_posts_scanned: int
    complaints: list[Complaint]
    errors: list[str] = Field(default_factory=list)
