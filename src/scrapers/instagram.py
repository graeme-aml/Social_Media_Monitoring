from datetime import datetime, timezone, timedelta

from apify_client import ApifyClient

from src.models import Post, Platform
from .base import BaseScraper


class InstagramScraper(BaseScraper):
    def __init__(self, client: ApifyClient, actor_id: str, max_results: int = 50):
        super().__init__(client, actor_id, max_results)

    def scrape(self, keywords: list[str], targets: list[str], lookback_hours: int) -> list[Post]:
        # Instagram scraper works by hashtag or profile URL
        hashtags = [kw.replace(" ", "") for kw in keywords if " " not in kw]
        profile_urls = [f"https://www.instagram.com/{t}/" for t in targets]

        run_input = {
            "hashtags": hashtags[:5],  # limit to avoid actor timeouts
            "directUrls": profile_urls,
            "resultsLimit": self.max_results,
            "onlyPostsNewerThan": (
                datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        raw_items = self._run_actor(run_input)
        return [self._to_post(item) for item in raw_items if item.get("caption")]

    def _to_post(self, item: dict) -> Post:
        ts = item.get("timestamp", "")
        try:
            created_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            created_at = datetime.now(timezone.utc)

        return Post(
            platform=Platform.INSTAGRAM,
            post_id=str(item.get("id", item.get("shortCode", ""))),
            text=item.get("caption", ""),
            author=item.get("ownerUsername", "unknown"),
            url=item.get("url", f"https://www.instagram.com/p/{item.get('shortCode', '')}/"),
            created_at=created_at,
            raw=item,
        )
