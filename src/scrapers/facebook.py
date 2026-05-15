from datetime import datetime, timezone, timedelta

from apify_client import ApifyClient

from src.models import Post, Platform
from .base import BaseScraper


class FacebookScraper(BaseScraper):
    def __init__(self, client: ApifyClient, actor_id: str, max_results: int = 50):
        super().__init__(client, actor_id, max_results)

    def scrape(self, keywords: list[str], targets: list[str], lookback_hours: int) -> list[Post]:
        # Facebook posts scraper works with page URLs
        page_urls = [f"https://www.facebook.com/{t}" for t in targets]

        run_input = {
            "startUrls": [{"url": url} for url in page_urls],
            "maxPosts": self.max_results,
            "onlyPostsOlderThan": "",
            "onlyPostsNewerThan": (
                datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            ).strftime("%Y-%m-%d"),
            "scrapeAbout": False,
            "scrapeReviews": True,
            "scrapeComments": True,
        }

        raw_items = self._run_actor(run_input)
        posts = []
        for item in raw_items:
            text = item.get("text") or item.get("message", "")
            if text:
                posts.append(self._to_post(item))
        return posts

    def _to_post(self, item: dict) -> Post:
        ts = item.get("time", "")
        try:
            created_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            created_at = datetime.now(timezone.utc)

        text = item.get("text") or item.get("message", "")
        return Post(
            platform=Platform.FACEBOOK,
            post_id=str(item.get("postId", item.get("id", ""))),
            text=text,
            author=item.get("user", {}).get("name", "unknown") if isinstance(item.get("user"), dict) else "unknown",
            url=item.get("url", ""),
            created_at=created_at,
            raw=item,
        )
