# Social Media Monitoring Agent

Monitors X (Twitter), Instagram, Facebook, and Bluesky for customer complaints about your brand, using [Apify](https://apify.com) actors for scraping and Claude AI for intelligent complaint analysis.

## Features

- Scrapes all four platforms via Apify actors (no direct API credentials needed per platform)
- Detects complaints via keyword matching + optional Claude AI analysis
- Classifies severity: **low / medium / high**
- Outputs to console (rich table), JSON files, and Slack webhooks
- Runs once or on a configurable schedule

## Quickstart

### 1. Install dependencies

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your APIFY_TOKEN and optionally ANTHROPIC_API_KEY
```

Get your Apify token at [apify.com/account/integrations](https://console.apify.com/account/integrations).

### 3. Configure monitoring targets

Edit `config/config.yaml`:

- Set `monitoring.targets` to your brand handles
- Add/remove keywords under `monitoring.keywords`
- Toggle platforms on/off under `platforms`
- Set `scheduling.interval_minutes` (0 = run once)

### 4. Run

```bash
# Run once
python main.py

# Run with a custom config
python main.py config/my_config.yaml

# Run on schedule (set interval_minutes in config)
python main.py
```

## Architecture

```
main.py                        # CLI entry point + scheduler
src/
  agent.py                     # Orchestrates scraping + analysis + reporting
  models.py                    # Pydantic models: Post, Complaint, MonitoringReport
  scrapers/
    base.py                    # BaseScraper with retry logic
    twitter.py                 # X/Twitter via apidojo/tweet-scraper
    instagram.py               # Instagram via apify/instagram-scraper
    facebook.py                # Facebook via apify/facebook-posts-scraper
    bluesky.py                 # Bluesky via blue-bot/bluesky-scraper
  analysis/
    complaint_detector.py      # Keyword + Claude AI complaint detection
  reporting/
    reporter.py                # Console (rich), JSON, Slack output
config/
  config.yaml                  # All configuration
tests/                         # pytest unit tests
```

## Apify Actors Used

| Platform | Actor |
|---|---|
| X / Twitter | [apidojo/tweet-scraper](https://apify.com/apidojo/tweet-scraper) |
| Instagram | [apify/instagram-scraper](https://apify.com/apify/instagram-scraper) |
| Facebook | [apify/facebook-posts-scraper](https://apify.com/apify/facebook-posts-scraper) |
| Bluesky | [blue-bot/bluesky-scraper](https://apify.com/blue-bot/bluesky-scraper) |

## Tests

```bash
pytest tests/ -v
```

## Adding a New Platform

1. Create `src/scrapers/yourplatform.py` extending `BaseScraper`
2. Implement `scrape()` returning `list[Post]`
3. Add the actor ID and config in `config/config.yaml`
4. Register the scraper in `src/agent.py`
