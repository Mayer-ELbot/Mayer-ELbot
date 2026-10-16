#!/usr/bin/env python3
"""
Mayer-ELbot Profile Auto-Updater
Fetches latest repository activity and releases, and dynamically injects them into README.md
"""

import json
import re
import urllib.request
from datetime import datetime, timezone

USERNAME = "Mayer-ELbot"
README_PATH = "README.md"
START_TAG = "<!-- AUTO_UPDATE:START -->"
END_TAG = "<!-- AUTO_UPDATE:END -->"

REPOS = [
    "GreenLuma-Stealth-Manager",
    "PC-Booster",
    "NightByte",
    "Website-for-AAST-material",
]

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mayer-Profile-Updater",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_latest_activity():
    events_url = f"https://api.github.com/users/{USERNAME}/events/public?per_page=15"
    events = fetch_json(events_url) or []
    
    activity_items = []
    seen_repos = set()

    for ev in events:
        ev_type = ev.get("type")
        repo_name = ev.get("repo", {}).get("name", "").replace(f"{USERNAME}/", "")
        created_at = ev.get("created_at", "")
        
        if not repo_name or repo_name == USERNAME:
            continue

        date_str = ""
        if created_at:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            date_str = dt.strftime("%b %d, %Y")

        if ev_type == "PushEvent" and repo_name not in seen_repos:
            commits = ev.get("payload", {}).get("commits", [])
            msg = commits[-1].get("message", "Updated codebase").split("\n")[0] if commits else "Pushed commits"
            if len(msg) > 60:
                msg = msg[:57] + "..."
            activity_items.append(f"- 🚀 **[{repo_name}](https://github.com/{USERNAME}/{repo_name})**: `{msg}` *({date_str})*")
            seen_repos.add(repo_name)
        elif ev_type == "ReleaseEvent":
            rel_name = ev.get("payload", {}).get("release", {}).get("name", "New Release")
            activity_items.append(f"- 📦 **[{repo_name}](https://github.com/{USERNAME}/{repo_name})**: Shipped **{rel_name}** *({date_str})*")

        if len(activity_items) >= 4:
            break

    if not activity_items:
        activity_items.append("- ⚡ *Actively shipping optimizations & local-first desktop tools.*")

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    output = [
        START_TAG,
        f"> 🔄 **Live Pulse (Auto-Updated):** `Last sync: {now_utc}`",
        "",
        *activity_items,
        END_TAG,
    ]
    return "\n".join(output)

def update_readme():
    try:
        with open(README_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        new_block = get_latest_activity()
        pattern = re.compile(f"{re.escape(START_TAG)}.*?{re.escape(END_TAG)}", re.DOTALL)

        if pattern.search(content):
            updated_content = pattern.sub(new_block, content)
            with open(README_PATH, "w", encoding="utf-8") as f:
                f.write(updated_content)
            print("Successfully updated README.md with live activity.")
        else:
            print("Auto-update tags not found in README.md.")
    except Exception as e:
        print(f"Failed to update README.md: {e}")

if __name__ == "__main__":
    update_readme()
