from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.scrapers.twitter import TwitterScraper
from src.scrapers.instagram import InstagramScraper
from src.scrapers.facebook import FacebookScraper
from src.scrapers.bluesky import BlueskyScraper
from src.models import Platform


SAMPLE_TWEET = {
    "id_str": "1234567890",
    "full_text": "This product is broken and customer service won't help!",
    "created_at": "Thu Jan 01 12:00:00 +0000 2026",
    "user": {"screen_name": "angry_user"},
}

SAMPLE_INSTA = {
    "id": "abc123",
    "shortCode": "abc123",
    "caption": "Worst purchase ever, totally disappointed.",
    "timestamp": "2026-01-01T12:00:00Z",
    "ownerUsername": "unhappy_customer",
    "url": "https://www.instagram.com/p/abc123/",
}

SAMPLE_FB = {
    "postId": "fb001",
    "text": "Awful experience with your delivery service!",
    "time": "2026-01-01T12:00:00Z",
    "user": {"name": "John Doe"},
    "url": "https://www.facebook.com/post/fb001",
}

SAMPLE_BLUESKY = {
    "uri": "at://did:plc:abc/app.bsky.feed.post/xyz",
    "text": "@brand your app is completely broken, scam!",
    "createdAt": "2026-01-01T12:00:00Z",
    "author": {"handle": "frustrated.bsky.social"},
}


def make_mock_client(items):
    mock_client = MagicMock()
    mock_run = {"defaultDatasetId": "dataset_id"}
    mock_client.actor.return_value.call.return_value = mock_run
    mock_client.dataset.return_value.iterate_items.return_value = iter(items)
    return mock_client


class TestTwitterScraper:
    def test_scrape_returns_posts(self):
        client = make_mock_client([SAMPLE_TWEET])
        scraper = TwitterScraper(client, "apidojo/tweet-scraper")
        posts = scraper.scrape(["broken"], ["TestBrand"], 24)
        assert len(posts) == 1
        assert posts[0].platform == Platform.TWITTER
        assert posts[0].author == "angry_user"


class TestInstagramScraper:
    def test_scrape_returns_posts(self):
        client = make_mock_client([SAMPLE_INSTA])
        scraper = InstagramScraper(client, "apify/instagram-scraper")
        posts = scraper.scrape(["disappointed"], ["TestBrand"], 24)
        assert len(posts) == 1
        assert posts[0].platform == Platform.INSTAGRAM


class TestFacebookScraper:
    def test_scrape_returns_posts(self):
        client = make_mock_client([SAMPLE_FB])
        scraper = FacebookScraper(client, "apify/facebook-posts-scraper")
        posts = scraper.scrape(["awful"], ["TestBrand"], 24)
        assert len(posts) == 1
        assert posts[0].platform == Platform.FACEBOOK


class TestBlueskyScraper:
    def test_scrape_returns_posts(self):
        client = make_mock_client([SAMPLE_BLUESKY])
        scraper = BlueskyScraper(client, "blue-bot/bluesky-scraper")
        posts = scraper.scrape(["broken"], ["brand"], 24)
        assert len(posts) == 1
        assert posts[0].platform == Platform.BLUESKY
        assert "bsky.app" in posts[0].url
