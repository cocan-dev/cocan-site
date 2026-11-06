#!/usr/bin/env python3
"""Regenerate the activity heatmap in index.html from public cocan-dev repos.

Run before pushing:  python scripts/update_activity.py
Needs the GitHub CLI (`gh`) signed in. Visitors' browsers make no requests:
the grid is written into index.html as plain HTML between the markers.
"""
import json, re, subprocess, datetime as dt
from collections import defaultdict
from pathlib import Path

ORG = "cocan-dev"
WEEKS = 26
START_MARK, END_MARK = "<!-- activity:start -->", "<!-- activity:end -->"
INDEX = Path(__file__).resolve().parent.parent / "index.html"


def gh(*args):
    out = subprocess.run(["gh", "api", *args], capture_output=True, text=True, check=True).stdout
    return out


def paged(path):
    # --paginate emits one JSON array per page; join them
    raw = gh("--paginate", path).strip()
    items = []
    for chunk in re.split(r"(?<=\])\s*(?=\[)", raw):
        if chunk:
            items += json.loads(chunk)
    return items


today = dt.datetime.now(dt.timezone.utc).date()
this_sunday = today - dt.timedelta(days=(today.weekday() + 1) % 7)
start = this_sunday - dt.timedelta(weeks=WEEKS - 1)

repos = [r["name"] for r in paged(f"orgs/{ORG}/repos?type=public&per_page=100")
         if not r["fork"] and not r["archived"]]
repos.sort()

counts = defaultdict(lambda: defaultdict(int))  # day -> repo -> n
for repo in repos:
    since = f"{start.isoformat()}T00:00:00Z"
    try:
        commits = paged(f"repos/{ORG}/{repo}/commits?since={since}&per_page=100")
    except subprocess.CalledProcessError:  # empty repo
        continue
    for c in commits:
        day = dt.date.fromisoformat(c["commit"]["author"]["date"][:10])
        counts[day][repo] += 1

total = sum(n for d in counts.values() for n in d.values())
active = len(counts)
cells = []
i = 0
for w in range(WEEKS):
    for d in range(7):
        day = start + dt.timedelta(weeks=w, days=d)
        delay = f' style="animation-delay:{w * 25 + d * 8}ms"'
        if day > today:
            cells.append('<i class="cell future"></i>')
            continue
        per = counts.get(day)
        if not per:
            cells.append(f'<i class="cell"{delay}></i>')
            continue
        top = max(per, key=lambda r: (per[r], r))
        n = sum(per.values())
        lvl = 1 if n == 1 else 2 if n <= 3 else 3 if n <= 6 else 4
        detail = ", ".join(f"{r} {k}" for r, k in sorted(per.items()))
        label = f"{day.isoformat()}: {n} commit{'s' if n != 1 else ''} ({detail})"
        cells.append(f'<i class="cell p{repos.index(top) % 3} l{lvl}" title="{label}"{delay}></i>')

legend = "".join(f'<a href="https://github.com/{ORG}/{r}"><i class="sw p{i % 3}"></i>{r}</a>' for i, r in enumerate(repos))
html = f'''{START_MARK}
      <figure class="activity" role="group" aria-label="Commit activity over the last {WEEKS} weeks">
        <figcaption>{total} commits on {active} days in the last {WEEKS} weeks</figcaption>
        <div class="grid" aria-hidden="true">{"".join(cells)}</div>
        <div class="legend">{legend}<span class="upd">updated {today.isoformat()}</span></div>
      </figure>
      {END_MARK}'''

text = INDEX.read_text(encoding="utf-8")
if START_MARK not in text:
    raise SystemExit("markers not found in index.html")
text = re.sub(re.escape(START_MARK) + r".*?" + re.escape(END_MARK), lambda m: html, text, flags=re.S)
INDEX.write_text(text, encoding="utf-8", newline="\n")
print(f"{len(repos)} repos ({', '.join(repos)}), {total} commits, {active} active days")
