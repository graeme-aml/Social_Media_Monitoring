#!/usr/bin/env python3
"""
Test screening runner.

Generates a realistic mock screening across all 6 platforms, uses Claude AI to
produce disposition recommendations, then creates a Jira epic + up to 10 tickets
on the CIM board.

Usage:
    export JIRA_EMAIL=graeme@lithic.com
    export JIRA_API_TOKEN=<your-token>
    export ANTHROPIC_API_KEY=<your-key>   # optional but recommended
    python scripts/run_test_screening.py
"""

import base64
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()

JIRA_BASE = "https://lithichq.atlassian.net"
JIRA_PROJECT = "CIM"
MAX_TICKETS = 10

# ---------------------------------------------------------------------------
# Mock complaint data — realistic sample of what the agent would surface
# ---------------------------------------------------------------------------

MOCK_COMPLAINTS = [
    {
        "platform": "twitter",
        "author": "frustrated_dave92",
        "text": "@YourBrand my card was declined AGAIN at the grocery store. Third time this week. Absolutely unacceptable 🤬 #CustomerService",
        "url": "https://twitter.com/frustrated_dave92/status/1234567890001",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
        "severity": "high",
        "matched_keywords": ["unacceptable", "customer service"],
    },
    {
        "platform": "twitter",
        "author": "angrymom_2kids",
        "text": "@YourBrand I’ve been waiting 10 DAYS for my refund. No response from support. This is a scam operation. Filing a complaint with CFPB.",
        "url": "https://twitter.com/angrymom_2kids/status/1234567890002",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=7)).isoformat(),
        "severity": "high",
        "matched_keywords": ["refund", "scam", "complaint"],
    },
    {
        "platform": "instagram",
        "author": "mike.travels.world",
        "text": "Worst experience with @YourBrand — card stopped working mid-trip abroad, support chat is completely broken, couldn’t reach anyone for 6 hours. Nearly stranded. Never again.",
        "url": "https://www.instagram.com/p/CabcDEfghIJ/",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
        "severity": "high",
        "matched_keywords": ["worst", "broken", "never again"],
    },
    {
        "platform": "facebook",
        "author": "Sandra Kowalski",
        "text": "YourBrand charged me twice for the same transaction. I’ve called support three times and nobody can explain why or when I’ll get my money back. Totally disappointed.",
        "url": "https://www.facebook.com/YourBrand/posts/10159123456789",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=18)).isoformat(),
        "severity": "high",
        "matched_keywords": ["disappointed", "refund"],
    },
    {
        "platform": "tiktok",
        "author": "crypto_kyle_official",
        "text": "POV: @YourBrand freezes your account with no warning and tells you to wait 30 business days for review. Zero explanation. This is FRAUD #fyp #fintech #scam",
        "url": "https://www.tiktok.com/@crypto_kyle_official/video/7123456789012345678",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
        "severity": "high",
        "matched_keywords": ["fraud", "scam"],
    },
    {
        "platform": "bluesky",
        "author": "techwriter.bsky.social",
        "text": "@yourbrand.bsky.social your app has been broken for 3 days and I can’t access my account. Support ticket still open with no update. Terrible service for a fintech.",
        "url": "https://bsky.app/profile/techwriter.bsky.social/post/3jxyz123abc",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=9)).isoformat(),
        "severity": "medium",
        "matched_keywords": ["broken", "terrible"],
    },
    {
        "platform": "twitch",
        "author": "StreamerJordan",
        "text": "anyone else having issues with YourBrand today? my card isn’t working for subs and donations. customer service said call back in 24h — not good enough",
        "url": "https://www.twitch.tv/YourBrand",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "severity": "medium",
        "matched_keywords": ["issues", "not working", "customer service"],
    },
    {
        "platform": "twitter",
        "author": "dev_building_startup",
        "text": "@YourBrand your API has been returning 503s for the past hour. Multiple clients affected. No status page update. This is unacceptable for a production dependency.",
        "url": "https://twitter.com/dev_building_startup/status/1234567890008",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        "severity": "high",
        "matched_keywords": ["unacceptable"],
    },
    {
        "platform": "instagram",
        "author": "small_biz_owner_rosa",
        "text": "@YourBrand I run a small business and your card reader stopped working during our busiest day of the year. Lost at least $2000 in sales. I need answers and compensation.",
        "url": "https://www.instagram.com/p/CxyzABC123/",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=14)).isoformat(),
        "severity": "high",
        "matched_keywords": ["not working", "problem"],
    },
    {
        "platform": "facebook",
        "author": "RetiredTeacherBob",
        "text": "WARNING to everyone — YourBrand has been impossible to reach. My account has been locked for two weeks and I cannot access my own money. This is criminal. Reporting to Better Business Bureau.",
        "url": "https://www.facebook.com/groups/fintechreviews/posts/10159987654321",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=22)).isoformat(),
        "severity": "high",
        "matched_keywords": ["complaint", "fraud"],
    },
]


# ---------------------------------------------------------------------------
# AI recommendation generation
# ---------------------------------------------------------------------------

def generate_recommendation(complaint: dict, anthropic_key: Optional[str]) -> str:
    if not anthropic_key:
        return _heuristic_recommendation(complaint)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=anthropic_key)
        prompt = f"""You are a customer experience analyst at a fintech company.

A social media monitoring agent flagged this post as a customer complaint:

Platform: {complaint['platform']}
Author: @{complaint['author']}
Severity: {complaint['severity']}
Matched keywords: {', '.join(complaint['matched_keywords'])}
Post text: {complaint['text']}
URL: {complaint['url']}

Provide a concise disposition recommendation (3-5 sentences) that includes:
1. Urgency level and suggested response time SLA
2. Which internal team should own this (e.g. Support, Compliance, Engineering, PR)
3. Suggested first response action
4. Whether regulatory/legal escalation is warranted

Be specific and actionable."""

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        console.print(f"[yellow]AI recommendation failed ({e}), using heuristic.[/yellow]")
        return _heuristic_recommendation(complaint)


def _heuristic_recommendation(complaint: dict) -> str:
    severity = complaint["severity"]
    keywords = set(complaint["matched_keywords"])
    platform = complaint["platform"]

    if any(k in keywords for k in ("scam", "fraud", "cfpb", "bbb", "lawsuit", "criminal", "reporting")):
        return (
            "URGENT — potential regulatory/legal exposure. Escalate immediately to Compliance and Legal. "
            "Respond publicly within 1 hour acknowledging the issue. Assign a dedicated support agent. "
            "Document all interactions for potential regulatory response."
        )
    if severity == "high":
        return (
            f"HIGH priority — respond within 2 hours. Assign to Senior Support team. "
            f"Post a public reply on {platform} acknowledging the issue and provide a direct support channel. "
            "Escalate to Engineering if service disruption is confirmed. Log in incident tracker."
        )
    return (
        f"MEDIUM priority — respond within 4 hours via {platform} DM and public reply. "
        "Assign to Support tier-1. Investigate account/transaction logs. "
        "Follow up within 24 hours with resolution."
    )


# ---------------------------------------------------------------------------
# Jira helpers
# ---------------------------------------------------------------------------

def jira_headers(email: str, token: str) -> dict:
    creds = base64.b64encode(f"{email}:{token}".encode()).decode()
    return {
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get_issue_type_id(client: httpx.Client, name: str) -> Optional[str]:
    r = client.get(f"{JIRA_BASE}/rest/api/3/project/{JIRA_PROJECT}")
    r.raise_for_status()
    for t in r.json().get("issueTypes", []):
        if t["name"].lower() == name.lower():
            return t["id"]
    return None


def create_epic(client: httpx.Client, run_at: str, total: int, epic_type_id: Optional[str]) -> dict:
    body: dict = {
        "fields": {
            "project": {"key": JIRA_PROJECT},
            "summary": f"Social Media Complaint Screening — {run_at}",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": (
                        f"Automated test screening run on {run_at}. "
                        f"{total} posts scanned across Twitter, Instagram, Facebook, Bluesky, TikTok, and Twitch. "
                        f"{min(total, MAX_TICKETS)} complaint tickets created below."
                    )}]
                }]
            },
            "issuetype": {"name": "Epic"} if not epic_type_id else {"id": epic_type_id},
        }
    }
    r = client.post(f"{JIRA_BASE}/rest/api/3/issue", json=body)
    if not r.is_success:
        console.print(f"[red]Epic creation failed ({r.status_code}): {r.text}[/red]")
        # Fall back to Task if Epic not available
        body["fields"]["issuetype"] = {"name": "Task"}
        r = client.post(f"{JIRA_BASE}/rest/api/3/issue", json=body)
        r.raise_for_status()
    return r.json()


SEVERITY_PRIORITY = {"high": "High", "medium": "Medium", "low": "Low"}


def create_ticket(client: httpx.Client, complaint: dict, recommendation: str, epic_key: str, index: int) -> dict:
    platform = complaint["platform"].capitalize()
    author = complaint["author"]
    severity = complaint["severity"].upper()
    keywords = ", ".join(complaint["matched_keywords"])
    url = complaint["url"]
    text = complaint["text"]

    summary = f"[{platform}] [{severity}] Complaint from @{author} — {text[:60]}{'...' if len(text) > 60 else ''}"

    description_content = [
        {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Complaint Details"}]},
        {"type": "paragraph", "content": [
            {"type": "text", "text": "Platform: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": platform},
        ]},
        {"type": "paragraph", "content": [
            {"type": "text", "text": "Author: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": f"@{author}"},
        ]},
        {"type": "paragraph", "content": [
            {"type": "text", "text": "Severity: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": severity},
        ]},
        {"type": "paragraph", "content": [
            {"type": "text", "text": "Matched Keywords: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": keywords},
        ]},
        {"type": "paragraph", "content": [
            {"type": "text", "text": "Post: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": text},
        ]},
        {"type": "paragraph", "content": [
            {"type": "text", "text": "URL: ", "marks": [{"type": "strong"}]},
            {"type": "text", "text": url, "marks": [{"type": "link", "attrs": {"href": url}}]},
        ]},
        {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Disposition Recommendation"}]},
        {"type": "paragraph", "content": [{"type": "text", "text": recommendation}]},
    ]

    body: dict = {
        "fields": {
            "project": {"key": JIRA_PROJECT},
            "summary": summary,
            "description": {"type": "doc", "version": 1, "content": description_content},
            "issuetype": {"name": "Task"},
            "priority": {"name": SEVERITY_PRIORITY.get(complaint["severity"], "Medium")},
            "labels": ["social-media-monitoring", complaint["platform"], complaint["severity"]],
        }
    }

    # Link to epic if possible
    if epic_key:
        body["fields"]["parent"] = {"key": epic_key}

    r = client.post(f"{JIRA_BASE}/rest/api/3/issue", json=body)
    if not r.is_success:
        # Try without parent (epic link field varies by Jira config)
        body["fields"].pop("parent", None)
        r = client.post(f"{JIRA_BASE}/rest/api/3/issue", json=body)
        r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    jira_email = os.environ.get("JIRA_EMAIL", "graeme@lithic.com")
    jira_token = os.environ.get("JIRA_API_TOKEN", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not jira_token:
        console.print("[red]JIRA_API_TOKEN environment variable is required.[/red]")
        sys.exit(1)

    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    complaints = MOCK_COMPLAINTS[:MAX_TICKETS]

    console.rule(f"[bold]Social Media Complaint Screening — {run_at}")
    console.print(f"Platforms: Twitter, Instagram, Facebook, Bluesky, TikTok, Twitch")
    console.print(f"Posts scanned (mock): {len(MOCK_COMPLAINTS)}  |  Complaints to ticket: {len(complaints)}")
    console.print()

    # Generate AI recommendations
    console.print("[bold]Generating disposition recommendations...[/bold]")
    recommendations = []
    for i, c in enumerate(complaints, 1):
        console.print(f"  [{i}/{len(complaints)}] @{c['author']} ({c['platform']})")
        rec = generate_recommendation(c, anthropic_key or None)
        recommendations.append(rec)

    # Print results table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", width=3)
    table.add_column("Platform", width=10)
    table.add_column("Author", width=22)
    table.add_column("Sev", width=6)
    table.add_column("Recommendation (truncated)", width=60)
    severity_color = {"high": "red", "medium": "orange3", "low": "yellow"}
    for i, (c, rec) in enumerate(zip(complaints, recommendations), 1):
        color = severity_color.get(c["severity"], "white")
        table.add_row(
            str(i),
            c["platform"],
            f"@{c['author']}",
            Text(c["severity"].upper(), style=color),
            rec[:57] + "..." if len(rec) > 57 else rec,
        )
    console.print(table)
    console.print()

    # Create Jira epic + tickets
    console.print("[bold]Creating Jira epic and tickets...[/bold]")
    headers = jira_headers(jira_email, jira_token)

    with httpx.Client(headers=headers, timeout=30) as client:
        # Create epic
        console.print("  Creating epic...")
        try:
            epic = create_epic(client, run_at, len(MOCK_COMPLAINTS), None)
            epic_key = epic.get("key", "")
            epic_url = f"{JIRA_BASE}/browse/{epic_key}"
            console.print(f"  [green]Epic created:[/green] {epic_key} — {epic_url}")
        except Exception as e:
            console.print(f"  [red]Failed to create epic: {e}[/red]")
            epic_key = ""
            epic_url = ""

        # Create tickets
        ticket_keys = []
        for i, (c, rec) in enumerate(zip(complaints, recommendations), 1):
            try:
                ticket = create_ticket(client, c, rec, epic_key, i)
                key = ticket.get("key", "")
                ticket_keys.append(key)
                console.print(f"  [{i}/{len(complaints)}] [green]{key}[/green] — @{c['author']} ({c['platform']}) [{c['severity'].upper()}]")
            except Exception as e:
                console.print(f"  [{i}/{len(complaints)}] [red]Failed: {e}[/red]")

    console.rule("[bold green]Done")
    if epic_url:
        console.print(f"Epic:    {epic_url}")
    for key in ticket_keys:
        console.print(f"Ticket:  {JIRA_BASE}/browse/{key}")


if __name__ == "__main__":
    main()
