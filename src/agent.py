import os
from datetime import datetime, timezone
from typing import Optional

import anthropic
from apify_client import ApifyClient
from rich.console import Console

from src.models import MonitoringReport, Platform
from src.scrapers import (
    TwitterScraper,
    InstagramScraper,
    FacebookScraper,
    BlueskyScraper,
    TikTokScraper,
    TwitchScraper,
)
from src.analysis import ComplaintDetector
from src.reporting import Reporter

console = Console()


class SocialMediaMonitoringAgent:
    def __init__(self, config: dict):
        self.config = config
        self.monitoring_cfg = config["monitoring"]
        self.platforms_cfg = config["platforms"]
        self.reporting_cfg = config["reporting"]

        apify_token = os.environ["APIFY_TOKEN"]
        self.apify_client = ApifyClient(apify_token)

        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key) if anthropic_key else None
        if not self.anthropic_client:
            console.print("[yellow]ANTHROPIC_API_KEY not set — using heuristic complaint detection.[/yellow]")

        self.detector = ComplaintDetector(
            anthropic_client=self.anthropic_client,
            min_confidence=self.monitoring_cfg["min_confidence"],
        )
        self.reporter = Reporter(self.reporting_cfg)

    def run(self) -> MonitoringReport:
        keywords: list[str] = self.monitoring_cfg["keywords"]
        targets: list[str] = self.monitoring_cfg["targets"]
        lookback: int = self.monitoring_cfg["lookback_hours"]

        all_posts = []
        platforms_scraped = []
        errors = []

        scrapers = {
            Platform.TWITTER: (
                "twitter",
                lambda cfg: TwitterScraper(self.apify_client, cfg["actor_id"], cfg["max_results"]),
            ),
            Platform.INSTAGRAM: (
                "instagram",
                lambda cfg: InstagramScraper(self.apify_client, cfg["actor_id"], cfg["max_results"]),
            ),
            Platform.FACEBOOK: (
                "facebook",
                lambda cfg: FacebookScraper(self.apify_client, cfg["actor_id"], cfg["max_results"]),
            ),
            Platform.BLUESKY: (
                "bluesky",
                lambda cfg: BlueskyScraper(self.apify_client, cfg["actor_id"], cfg["max_results"]),
            ),
            Platform.TIKTOK: (
                "tiktok",
                lambda cfg: TikTokScraper(self.apify_client, cfg["actor_id"], cfg["max_results"]),
            ),
            Platform.TWITCH: (
                "twitch",
                lambda cfg: TwitchScraper(self.apify_client, cfg["actor_id"], cfg["max_results"]),
            ),
        }

        for platform, (cfg_key, scraper_factory) in scrapers.items():
            platform_cfg = self.platforms_cfg.get(cfg_key, {})
            if not platform_cfg.get("enabled", False):
                continue

            console.print(f"Scraping [bold]{platform.value}[/bold]...")
            try:
                scraper = scraper_factory(platform_cfg)
                posts = scraper.scrape(keywords, targets, lookback)
                console.print(f"  Found {len(posts)} posts on {platform.value}")
                all_posts.extend(posts)
                platforms_scraped.append(platform)
            except Exception as e:
                msg = f"Failed to scrape {platform.value}: {e}"
                console.print(f"[red]{msg}[/red]")
                errors.append(msg)

        console.print(f"\nAnalysing {len(all_posts)} posts for complaints...")
        complaints = []
        for post in all_posts:
            complaint = self.detector.analyze(post, keywords)
            if complaint:
                complaints.append(complaint)

        report = MonitoringReport(
            run_at=datetime.now(timezone.utc),
            platforms_scraped=platforms_scraped,
            total_posts_scanned=len(all_posts),
            complaints=complaints,
            errors=errors,
        )

        self.reporter.publish(report)
        return report
