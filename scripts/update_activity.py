#!/usr/bin/env python3
"""Regenerate the project cards in index.html from public cocan-dev repos.

Run before pushing:  python scripts/update_activity.py
Needs the GitHub CLI (`gh`) signed in. Visitors' browsers make no requests:
the cards are written into index.html as plain HTML between the markers.
"""
import html, json, re, subprocess, datetime as dt
from collections import Counter
from pathlib import Path

ORG = "cocan-dev"
WEEKS = 12      # length of each card's activity strip
MAX_CARDS = 6   # most recently active projects shown
START_MARK, END_MARK = "<!-- activity:start -->", "<!-- activity:end -->"
INDEX = Path(__file__).resolve().parent.parent / "index.html"
# Repos that are not "projects" (e.g. this website) can be listed here.
HIDE = set()


def paged(path):
    raw = subprocess.run(["gh", "api", "--paginate", path], capture_output=True, text=True, check=True).stdout.strip()
    items = []
    for chunk in re.split(r"(?<=\])\s*(?=\[)", raw):
        if chunk:
            items += json.loads(chunk)
    return items


def d(s):
    return dt.date.fromisoformat(s[:10])


def fmt(day):
    return f"{day.day} {day.strftime('%b %Y')}"


today = dt.datetime.now(dt.timezone.utc).date()
this_sunday = today - dt.timedelta(days=(today.weekday() + 1) % 7)
first_week = this_sunday - dt.timedelta(weeks=WEEKS - 1)

projects = []
for r in paged(f"orgs/{ORG}/repos?type=public&per_page=100"):
    if r["fork"] or r["archived"] or r["name"] in HIDE:
        continue
    try:
        commits = paged(f"repos/{ORG}/{r['name']}/commits?per_page=100")
    except subprocess.CalledProcessError:  # empty repo
        commits = []
    if not commits:
        continue
    weekly = Counter()
    for c in commits:
        day = d(c["commit"]["author"]["date"])
        wk = day - dt.timedelta(days=(day.weekday() + 1) % 7)
        weekly[wk] += 1
    projects.append(dict(
        name=r["name"], desc=r["description"] or "", url=r["html_url"],
        lic=(r.get("license") or {}).get("spdx_id") or "",
        total=len(commits), last=d(commits[0]["commit"]["author"]["date"]),
        recent=[(d(c["commit"]["author"]["date"]), c["commit"]["message"].splitlines()[0]) for c in commits[:1]],
        weekly=weekly))

projects.sort(key=lambda p: (p["last"], p["name"]), reverse=True)
shown = projects[:MAX_CARDS]
colour = {p["name"]: i % 3 for i, p in enumerate(sorted(projects, key=lambda p: p["name"]))}


def card(p):
    e = html.escape
    wk = [p["weekly"].get(first_week + dt.timedelta(weeks=i), 0) for i in range(WEEKS)]
    peak = max(wk) or 1
    bars = "".join(
        f'<i class="bar{" on" if n else ""}" style="--h:{max(12, round(100 * n / peak))}%;--i:{i}" '
        f'title="week of {fmt(first_week + dt.timedelta(weeks=i))}: {n} commit{"s" if n != 1 else ""}"></i>'
        for i, n in enumerate(wk))
    log = "".join(
        f'<li><time datetime="{day}">{fmt(day)}</time> {e(msg[:70] + ("…" if len(msg) > 70 else ""))}</li>'
        for day, msg in p["recent"])
    live = ' live' if (today - p["last"]).days <= 14 else ''
    lic = f'<span class="badge">{e(p["lic"])}</span>' if p["lic"] and p["lic"] != "NOASSERTION" else ""
    return f'''        <li class="proj p{colour[p["name"]]}{live}">
          <div class="head"><span class="led" aria-hidden="true"></span><h3><a href="{e(p["url"])}">{e(p["name"])}</a></h3>{lic}</div>
          <p class="desc">{e(p["desc"])}</p>
          <div class="bars" role="img" aria-label="{p["total"]} commits, weekly activity over the last {WEEKS} weeks">{bars}</div>
          <ul class="log">{log}</ul>
          <p class="meta">{p["total"]} commits · last {fmt(p["last"])}</p>
        </li>'''


more = (f'\n      <p class="more"><a href="https://github.com/{ORG}">All repositories on GitHub →</a></p>')
out = f'''{START_MARK}
      <ul class="projects">
{chr(10).join(card(p) for p in shown)}
      </ul>{more}
      {END_MARK}'''
text = INDEX.read_text(encoding="utf-8")
if START_MARK not in text:
    raise SystemExit("markers not found in index.html")
text = re.sub(re.escape(START_MARK) + r".*?" + re.escape(END_MARK), lambda m: out, text, flags=re.S)
INDEX.write_text(text, encoding="utf-8", newline="\n")
print(f"{len(shown)} of {len(projects)} projects: " + ", ".join(p['name'] for p in shown))
