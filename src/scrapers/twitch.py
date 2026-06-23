from datetime import datetime, timezone, timedelta

from apify_client import ApifyClient

from src.models import Post, Platform
from .base import BaseScraper


class TwitchScraper(BaseScraper):
    """Scrapes Twitch chat/clip comments via the pogreb/twitch-scraper Apify actor."""

    def __init__(self, client: ApifyClient, actor_id: str, max_results: int = 100):
        super().__init__(client, actor_id, max_results)

    def scrape(self, keywords: list[str], targets: list[str], lookback_hours: int) -> list[Post]:
        # Twitch scraper works by channel name; keywords are filtered client-side
        # because Twitch chat search is not keyword-based
        channel_urls = [f"https://www.twitch.tv/{t}" for t in targets]

        run_input = {
            "startUrls": [{"url": url} for url in channel_urls],
            "maxComments": self.max_results,
        }

        raw_items = self._run_actor(run_input)
        since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        lower_keywords = [kw.lower() for kw in keywords]

        posts = []
        for item in raw_items:
            text = item.get("text", item.get("message", ""))
            if not text:
                continue
            # Filter to items that mention at least one keyword (Twitch has no server-side search)
            if not any(kw in text.lower() for kw in lower_keywords):
                continue
            post = self._to_post(item)
            if post.created_at >= since:
                posts.append(post)
        return posts

    def _to_post(self, item: dict) -> Post:
        ts = item.get("createdAt", item.get("timestamp", ""))
        try:
            created_at = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            created_at = datetime.now(timezone.utc)

        channel = item.get("channelName", item.get("channel", "unknown"))
        author = item.get("authorName", item.get("commenter", {}).get("displayName", "unknown")) \
            if not isinstance(item.get("commenter"), dict) \
            else item["commenter"].get("displayName", "unknown")
        comment_id = str(item.get("id", ""))
        url = f"https://www.twitch.tv/{channel}"

        return Post(
            platform=Platform.TWITCH,
            post_id=comment_id,
            text=item.get("text", item.get("message", "")),
            author=author,
            url=url,
            created_at=created_at,
            raw=item,
        )
