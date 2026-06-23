from abc import ABC, abstractmethod
from typing import Any

from apify_client import ApifyClient
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models import Post


class BaseScraper(ABC):
    def __init__(self, client: ApifyClient, actor_id: str, max_results: int = 100):
        self.client = client
        self.actor_id = actor_id
        self.max_results = max_results

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
    def _run_actor(self, run_input: dict[str, Any]) -> list[dict]:
        run = self.client.actor(self.actor_id).call(run_input=run_input)
        items = list(
            self.client.dataset(run["defaultDatasetId"]).iterate_items()
        )
        return items

    @abstractmethod
    def scrape(self, keywords: list[str], targets: list[str], lookback_hours: int) -> list[Post]:
        """Scrape posts matching keywords/targets from this platform."""
        ...
