from datetime import datetime, timezone, timedelta

from apify_client import ApifyClient

from src.models import Post, Platform
from .base import BaseScraper


class BlueskyScraper(BaseScraper):
    def __init__(self, client: ApifyClient, actor_id: str, max_results: int = 100):
        super().__init__(client, actor_id, max_results)

    def scrape(self, keywords: list[str], targets: list[str], lookback_hours: int) -> list[Post]:
        # Bluesky scraper searches by keyword queries
        queries = keywords + targets

        run_input = {
            "queries": queries[:10],
            "maxPostsPerQuery": max(1, self.max_results // len(queries[:10])),
            "since": (
                datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        raw_items = self._run_actor(run_input)
        return [self._to_post(item) for item in raw_items if item.get("text")]

    def _to_post(self, item: dict) -> Post:
        ts = item.get("createdAt", item.get("indexedAt", ""))
        try:
            created_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            created_at = datetime.now(timezone.utc)

        handle = item.get("author", {}).get("handle", "unknown") if isinstance(item.get("author"), dict) else "unknown"
        uri = item.get("uri", "")
        # Convert at:// URI to bsky.app URL
        if uri.startswith("at://"):
            parts = uri.replace("at://", "").split("/")
            url = f"https://bsky.app/profile/{parts[0]}/post/{parts[-1]}" if len(parts) >= 3 else ""
        else:
            url = uri

        return Post(
            platform=Platform.BLUESKY,
            post_id=uri,
            text=item.get("text", ""),
            author=handle,
            url=url,
            created_at=created_at,
            raw=item,
        )
