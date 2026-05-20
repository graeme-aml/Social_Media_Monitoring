from datetime import datetime, timezone, timedelta

from apify_client import ApifyClient

from src.models import Post, Platform
from .base import BaseScraper


class TikTokScraper(BaseScraper):
    def __init__(self, client: ApifyClient, actor_id: str, max_results: int = 50):
        super().__init__(client, actor_id, max_results)

    def scrape(self, keywords: list[str], targets: list[str], lookback_hours: int) -> list[Post]:
        # TikTok scraper searches by hashtag and/or profile username
        hashtags = [f"#{kw.replace(' ', '')}" for kw in keywords if len(kw) <= 30]
        profile_urls = [f"https://www.tiktok.com/@{t}" for t in targets]

        run_input = {
            "hashtags": hashtags[:5],
            "profiles": profile_urls,
            "resultsPerPage": self.max_results,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }

        raw_items = self._run_actor(run_input)
        since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        return [
            self._to_post(item) for item in raw_items
            if item.get("text") and self._parse_ts(item) >= since
        ]

    def _parse_ts(self, item: dict) -> datetime:
        ts = item.get("createTime", item.get("createTimeISO", ""))
        # createTime is a Unix timestamp integer
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        try:
            return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return datetime.now(timezone.utc)

    def _to_post(self, item: dict) -> Post:
        video_id = str(item.get("id", ""))
        author = item.get("authorMeta", {}).get("name", "unknown") if isinstance(item.get("authorMeta"), dict) else "unknown"
        url = item.get("webVideoUrl", f"https://www.tiktok.com/@{author}/video/{video_id}")

        return Post(
            platform=Platform.TIKTOK,
            post_id=video_id,
            text=item.get("text", ""),
            author=author,
            url=url,
            created_at=self._parse_ts(item),
            raw=item,
        )
