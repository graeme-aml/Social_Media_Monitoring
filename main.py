#!/usr/bin/env python3
"""Entry point for the Social Media Monitoring Agent."""
import sys
import time
from pathlib import Path

import schedule
import yaml
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

console = Console()


def load_config(path: str = "config/config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def run_agent(config: dict) -> None:
    from src.agent import SocialMediaMonitoringAgent
    agent = SocialMediaMonitoringAgent(config)
    agent.run()


def main() -> None:
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/config.yaml"
    if not Path(config_path).exists():
        console.print(f"[red]Config file not found: {config_path}[/red]")
        sys.exit(1)

    config = load_config(config_path)
    interval: int = config.get("scheduling", {}).get("interval_minutes", 0)

    if interval <= 0:
        console.print("Running once...")
        run_agent(config)
        return

    console.print(f"[green]Scheduling monitoring every {interval} minutes.[/green]")
    run_agent(config)  # run immediately on start

    schedule.every(interval).minutes.do(run_agent, config=config)
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
