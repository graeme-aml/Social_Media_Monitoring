import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from rich.console import Console
from rich.table import Table
from rich.text import Text

from src.models import MonitoringReport, Severity

console = Console()

SEVERITY_COLOR = {
    Severity.LOW: "yellow",
    Severity.MEDIUM: "orange3",
    Severity.HIGH: "red",
}


class Reporter:
    def __init__(self, config: dict):
        self.config = config
        self.outputs: list[str] = config.get("outputs", ["console"])
        self.json_dir = Path(config.get("json_output_dir", "./reports"))
        self.alert_threshold = Severity(config.get("alert_threshold", "medium"))
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "")

    def publish(self, report: MonitoringReport) -> None:
        if "console" in self.outputs:
            self._print_console(report)
        if "json" in self.outputs:
            self._write_json(report)
        if "slack" in self.outputs and self.slack_webhook:
            self._send_slack(report)

    def _print_console(self, report: MonitoringReport) -> None:
        console.rule(f"[bold]Social Media Monitoring Report — {report.run_at.strftime('%Y-%m-%d %H:%M UTC')}")
        console.print(f"Platforms: {', '.join(p.value for p in report.platforms_scraped)}")
        console.print(f"Posts scanned: {report.total_posts_scanned}  |  Complaints found: {len(report.complaints)}")

        if report.errors:
            for err in report.errors:
                console.print(f"[red]ERROR:[/red] {err}")

        if not report.complaints:
            console.print("[green]No complaints detected.[/green]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Platform", width=10)
        table.add_column("Author", width=20)
        table.add_column("Severity", width=8)
        table.add_column("Confidence", width=10)
        table.add_column("Summary", width=50)
        table.add_column("URL", width=40)

        for c in sorted(report.complaints, key=lambda x: x.severity.value, reverse=True):
            color = SEVERITY_COLOR[c.severity]
            table.add_row(
                c.post.platform.value,
                f"@{c.post.author}",
                Text(c.severity.value.upper(), style=color),
                f"{c.confidence:.0%}",
                c.summary,
                c.post.url,
            )

        console.print(table)

    def _write_json(self, report: MonitoringReport) -> None:
        self.json_dir.mkdir(parents=True, exist_ok=True)
        filename = self.json_dir / f"report_{report.run_at.strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w") as f:
            json.dump(report.model_dump(mode="json"), f, indent=2, default=str)
        console.print(f"[dim]Report saved to {filename}[/dim]")

    def _send_slack(self, report: MonitoringReport) -> None:
        threshold_order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH]
        threshold_idx = threshold_order.index(self.alert_threshold)
        alerts = [
            c for c in report.complaints
            if threshold_order.index(c.severity) >= threshold_idx
        ]
        if not alerts:
            return

        lines = [f"*Social Media Complaints — {report.run_at.strftime('%Y-%m-%d %H:%M UTC')}*"]
        for c in alerts:
            emoji = {Severity.HIGH: ":red_circle:", Severity.MEDIUM: ":large_orange_circle:", Severity.LOW: ":yellow_circle:"}[c.severity]
            lines.append(f"{emoji} *{c.post.platform.value}* @{c.post.author} [{c.severity.value.upper()}] — {c.summary}")
            lines.append(f"   <{c.post.url}|View post>")

        payload = {"text": "\n".join(lines)}
        try:
            httpx.post(self.slack_webhook, json=payload, timeout=10)
        except httpx.HTTPError as e:
            console.print(f"[red]Slack notification failed: {e}[/red]")
