#!/usr/bin/env python3
"""
Custom GitHub Streak & Freeze Engine
Features Duolingo-style weekly streak freezes, longest vacation tracking, and custom SVG generation.
"""

import json
import os
import urllib.request
from datetime import datetime, timezone

USERNAME = "Mayer-ELbot"
OUTPUT_SVG = "assets/streak_card.svg"

def fetch_contributions():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        try:
            token = os.popen("gh auth token").read().strip()
        except Exception:
            token = None

    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                weekday
              }
            }
          }
        }
      }
    }
    """
    headers = {
        "User-Agent": "Mayer-Streak-Engine",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USERNAME}}).encode("utf-8"),
        headers=headers,
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    except Exception as e:
        print(f"Error querying GraphQL API: {e}")
        return None

def compute_streak_with_freezes(cal_data):
    if not cal_data:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "total_contributions": 0,
            "freezes_remaining": 2,
            "freezes_used_this_week": 0,
            "longest_rest_days": 0,
            "active_days": 0,
            "total_days": 0,
        }

    days = []
    for w in cal_data.get("weeks", []):
        for d in w.get("contributionDays", []):
            days.append({
                "date": d["date"],
                "count": d["contributionCount"],
                "weekday": d["weekday"],  # 0 is Sunday, 1 is Monday ... 6 is Saturday
                "dt": datetime.strptime(d["date"], "%Y-%m-%d"),
            })

    days.sort(key=lambda x: x["dt"])

    # Track streaks and freezes
    # Every Monday (weekday 1) gives 2 freeze shields
    current_streak = 0
    longest_streak = 0
    current_rest_period = 0
    longest_rest_days = 0
    active_days_count = 0

    weekly_freezes = 2
    freezes_used_this_week = 0
    last_week_num = None

    for day in days:
        dt = day["dt"]
        count = day["count"]
        week_num = dt.isocalendar()[1]

        # Reset weekly freeze on new ISO week (starts Monday)
        if week_num != last_week_num:
            weekly_freezes = 2
            freezes_used_this_week = 0
            last_week_num = week_num

        if count > 0:
            active_days_count += 1
            current_streak += 1
            if current_streak > longest_streak:
                longest_streak = current_streak
            current_rest_period = 0
        else:
            # 0 contributions: can we freeze?
            current_rest_period += 1
            if current_rest_period > longest_rest_days:
                longest_rest_days = current_rest_period

            if weekly_freezes > 0:
                weekly_freezes -= 1
                freezes_used_this_week += 1
                # Streak preserved by freeze!
                current_streak += 1
                if current_streak > longest_streak:
                    longest_streak = current_streak
            else:
                # No freezes left: streak broken
                current_streak = 0

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_contributions": cal_data.get("totalContributions", 0),
        "freezes_remaining": weekly_freezes,
        "freezes_used_this_week": freezes_used_this_week,
        "longest_rest_days": longest_rest_days,
        "active_days": active_days_count,
        "total_days": len(days),
    }

def render_svg(stats):
    curr = stats["current_streak"]
    longest = stats["longest_streak"]
    total = stats["total_contributions"]
    freezes_rem = stats["freezes_remaining"]
    freezes_used = stats["freezes_used_this_week"]
    longest_rest = stats["longest_rest_days"]
    active_days = stats["active_days"]
    total_days = max(stats["total_days"], 1)
    consistency = int((active_days / total_days) * 100)

    # Freeze display
    freeze_icons = "❄️ ❄️" if freezes_rem == 2 else ("❄️ 🛡️" if freezes_rem == 1 else "🛡️ ⚡")
    freeze_text = f"{freezes_rem}/2 Ready" if freezes_rem > 0 else "0/2 Used"

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 185" width="100%" height="100%">
  <defs>
    <linearGradient id="streakBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#080C14"/>
      <stop offset="50%" stop-color="#0F172A"/>
      <stop offset="100%" stop-color="#090D18"/>
    </linearGradient>

    <linearGradient id="fireGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#F59E0B"/>
      <stop offset="50%" stop-color="#EF4444"/>
      <stop offset="100%" stop-color="#EC4899"/>
    </linearGradient>

    <linearGradient id="iceGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00F0FF"/>
      <stop offset="100%" stop-color="#3B82F6"/>
    </linearGradient>

    <linearGradient id="borderGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00F0FF" stop-opacity="0.8"/>
      <stop offset="50%" stop-color="#8B5CF6" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#F59E0B" stop-opacity="0.8"/>
    </linearGradient>

    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <style>
    .mono {{
      font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', Consolas, monospace;
    }}
    @keyframes pulseFlame {{
      0%, 100% {{ transform: scale(1); opacity: 1; }}
      50% {{ transform: scale(1.08); opacity: 0.85; }}
    }}
    .flame-icon {{
      animation: pulseFlame 1.8s ease-in-out infinite;
      transform-origin: 48px 60px;
    }}
  </style>

  <!-- Container Box -->
  <rect width="850" height="185" rx="14" fill="url(#streakBg)" />
  <rect x="1" y="1" width="848" height="183" rx="13" fill="none" stroke="url(#borderGrad)" stroke-width="1.2" />

  <!-- Top Header Bar -->
  <g transform="translate(24, 20)">
    <text x="0" y="10" fill="#F8FAFC" font-size="13" class="mono" font-weight="700" letter-spacing="1">
      ⚡ DEV PULSE &amp; STREAK SHIELD DASHBOARD
    </text>
    <text x="560" y="10" fill="#64748B" font-size="10" class="mono">
      WEEKLY FREEZE PROTOCOL: ACTIVE
    </text>
  </g>
  <line x1="24" y1="40" x2="826" y2="40" stroke="#1E293B" stroke-width="1" />

  <!-- 4 Metric Cards Grid -->
  <!-- 1. Current Active Streak -->
  <g transform="translate(24, 52)">
    <rect width="188" height="85" rx="8" fill="#111827" stroke="#1F2937" stroke-width="1"/>
    <text x="14" y="24" fill="#94A3B8" font-size="10" class="mono" font-weight="600">🔥 ACTIVE STREAK</text>
    <text x="14" y="62" fill="url(#fireGrad)" font-size="32" class="mono" font-weight="900">{curr}</text>
    <text x="75" y="60" fill="#64748B" font-size="13" class="mono">DAYS</text>
  </g>

  <!-- 2. Streak Freeze Shields -->
  <g transform="translate(226, 52)">
    <rect width="188" height="85" rx="8" fill="#111827" stroke="#1F2937" stroke-width="1"/>
    <text x="14" y="24" fill="#94A3B8" font-size="10" class="mono" font-weight="600">❄️ STREAK FREEZE</text>
    <text x="14" y="60" fill="url(#iceGrad)" font-size="24" class="mono" font-weight="900">{freeze_icons}</text>
    <text x="100" y="58" fill="#38BDF8" font-size="11" class="mono" font-weight="700">{freeze_text}</text>
    <text x="14" y="76" fill="#64748B" font-size="9" class="mono">Refreshes every Monday</text>
  </g>

  <!-- 3. Longest Streak Record -->
  <g transform="translate(428, 52)">
    <rect width="188" height="85" rx="8" fill="#111827" stroke="#1F2937" stroke-width="1"/>
    <text x="14" y="24" fill="#94A3B8" font-size="10" class="mono" font-weight="600">🏆 LONGEST STREAK</text>
    <text x="14" y="62" fill="#FACC15" font-size="32" class="mono" font-weight="900">{longest}</text>
    <text x="80" y="60" fill="#64748B" font-size="13" class="mono">DAYS</text>
  </g>

  <!-- 4. Max Rest / Break Period -->
  <g transform="translate(630, 52)">
    <rect width="196" height="85" rx="8" fill="#111827" stroke="#1F2937" stroke-width="1"/>
    <text x="14" y="24" fill="#94A3B8" font-size="10" class="mono" font-weight="600">🏖️ MAX VACATION BREAK</text>
    <text x="14" y="62" fill="#34D399" font-size="32" class="mono" font-weight="900">{longest_rest}</text>
    <text x="65" y="60" fill="#64748B" font-size="13" class="mono">DAYS OFF</text>
  </g>

  <!-- Bottom Details Bar -->
  <g transform="translate(24, 158)">
    <text x="0" y="10" fill="#38BDF8" font-size="10" class="mono">
      🛡️ Freezes Used This Cycle: <tspan fill="#F8FAFC" font-weight="700">{freezes_used} used</tspan>
    </text>
    <text x="310" y="10" fill="#94A3B8" font-size="10" class="mono">
      • Annual Contributions: <tspan fill="#00F0FF" font-weight="700">{total} commits</tspan>
    </text>
    <text x="590" y="10" fill="#94A3B8" font-size="10" class="mono">
      • Consistency Score: <tspan fill="#10B981" font-weight="700">{consistency}%</tspan>
    </text>
  </g>
</svg>"""

    with open(OUTPUT_SVG, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated {OUTPUT_SVG} successfully.")

if __name__ == "__main__":
    cal = fetch_contributions()
    stats = compute_streak_with_freezes(cal)
    print("Computed stats:", stats)
    render_svg(stats)
