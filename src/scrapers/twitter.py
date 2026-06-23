from datetime import datetime, timezone, timedelta

from apify_client import ApifyClient

from src.models import Post, Platform
from .base import BaseScraper


class TwitterScraper(BaseScraper):
    def __init__(self, client: ApifyClient, actor_id: str, max_results: int = 100):
        super().__init__(client, actor_id, max_results)

    def scrape(self, keywords: list[str], targets: list[str], lookback_hours: int) -> list[Post]:
        # Build search queries: keywords + @mentions of targets
        queries = keywords + [f"@{t}" for t in targets]
        search_terms = " OR ".join(f'"{q}"' for q in queries[:10])  # Twitter limits

        since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        run_input = {
            "searchTerms": [search_terms],
            "maxTweets": self.max_results,
            "since": since.strftime("%Y-%m-%d"),
            "lang": "en",
        }

        raw_items = self._run_actor(run_input)
        return [self._to_post(item) for item in raw_items if item.get("full_text")]

    def _to_post(self, item: dict) -> Post:
        created_raw = item.get("created_at", "")
        try:
            created_at = datetime.strptime(created_raw, "%a %b %d %H:%M:%S %z %Y")
        except (ValueError, TypeError):
            created_at = datetime.now(timezone.utc)

        return Post(
            platform=Platform.TWITTER,
            post_id=str(item.get("id_str", item.get("id", ""))),
            text=item.get("full_text", item.get("text", "")),
            author=item.get("user", {}).get("screen_name", "unknown"),
            url=f"https://twitter.com/i/web/status/{item.get('id_str', '')}",
            created_at=created_at,
            raw=item,
        )
