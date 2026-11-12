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
MAX_CARDS = 6   # most recently active projects shown
START_MARK, END_MARK = "<!-- activity:start -->", "<!-- activity:end -->"
INDEX = Path(__file__).resolve().parent.parent / "index.html"
# Repos that are not "projects" (e.g. this website) can be listed here.
HIDE = {"kirpitch-site"}


def paged(path):
    raw = subprocess.run(["gh", "api", "--paginate", path], capture_output=True, text=True, check=True).stdout.strip()
    items = []
    for chunk in re.split(r"(?<=\])\s*(?=\[)", raw):
        if chunk:
            items += json.loads(chunk)
    return items


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def fmt(day):
    return f"{day.day} {day.strftime('%b %Y')}"


now = dt.datetime.now(dt.timezone.utc)
today = now.date()


def sunday(day):
    return day - dt.timedelta(days=(day.weekday() + 1) % 7)


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
    times = [ts(c["commit"]["author"]["date"]) for c in commits]
    projects.append(dict(
        name=r["name"], desc=r["description"] or "", url=r["html_url"], home=(r.get("homepage") or "").strip(),
        lic=(r.get("license") or {}).get("spdx_id") or "",
        total=len(times), last=max(times), first=min(times), times=times))

projects.sort(key=lambda p: (p["last"], p["name"]), reverse=True)
shown = projects[:MAX_CARDS]
colour = {p["name"]: i % 3 for i, p in enumerate(sorted(projects, key=lambda p: p["name"]))}


def level(n):
    return 1 if n == 1 else 2 if n <= 3 else 3 if n <= 6 else 4


def bars(counts, labels, isos=None):
    # isos: optional UTC hour starts; grid.js rewrites those tooltips in the visitor's time zone
    peak = max(counts) or 1
    return "".join(
        f'<i class="bar{" on" if n else ""}" style="--h:{max(12, round(100 * n / peak))}%;--i:{i}" '
        f'{f"data-h={chr(34)}{isos[i]}{chr(34)} data-n={chr(34)}{n}{chr(34)} " if isos else ""}'
        f'title="{lab}: {n} commit{"s" if n != 1 else ""}"></i>'
        for i, (n, lab) in enumerate(zip(counts, labels)))


def graph(p):
    """Pick the granularity from the project's age: hourly, then daily, then weekly."""
    age = now - p["first"]
    if age < dt.timedelta(days=3):  # just started: hourly bars, last 48 h
        hours = Counter(t.replace(minute=0, second=0, microsecond=0) for t in p["times"])
        slots = [now.replace(minute=0, second=0, microsecond=0) - dt.timedelta(hours=47 - i) for i in range(48)]
        return "hourly", "last 48 hours", f'<div class="bars">{bars([hours[h] for h in slots], [f"{fmt(h.date())} {h:%H}:00 UTC" for h in slots], [f"{h:%Y-%m-%dT%H}:00:00Z" for h in slots])}</div>'
    if age < dt.timedelta(weeks=12):  # young: daily calendar matrix, 12 weeks
        days = Counter(t.date() for t in p["times"])
        start = sunday(today) - dt.timedelta(weeks=11)
        cells = []
        for w in range(12):
            for dd in range(7):
                day = start + dt.timedelta(weeks=w, days=dd)
                n = days.get(day, 0)
                if day > today:
                    cells.append('<i class="cell future"></i>')
                else:
                    cls = f"cell on l{level(n)}" if n else "cell"
                    cells.append(f'<i class="{cls}" style="--i:{w}" title="{fmt(day)}: {n} commit{"s" if n != 1 else ""}"></i>')
        return "daily", "last 12 weeks", f'<div class="matrix">{"".join(cells)}</div>'
    weeks = Counter(sunday(t.date()) for t in p["times"])  # established: weekly bars, 52 weeks
    slots = [sunday(today) - dt.timedelta(weeks=51 - i) for i in range(52)]
    return "weekly", "last 52 weeks", f'<div class="bars">{bars([weeks[w] for w in slots], [f"week of {fmt(w)}" for w in slots])}</div>'


def fmt(day):
    return f"{day.day} {day.strftime('%b %Y')}"


def card(p):
    e = html.escape
    unit, span, g = graph(p)
    live = " live" if (now - p["last"]).days <= 14 else ""
    lic = f'<span class="badge">{e(p["lic"])}</span>' if p["lic"] and p["lic"] != "NOASSERTION" else ""
    home = f'<a class="site" href="{e(p["home"])}">{e(re.sub(r"^https?://|/$", "", p["home"]))}</a>' if p["home"].startswith("https://") else ""
    return f'''        <li class="proj p{colour[p["name"]]}{live}">
          <div class="head"><span class="led" aria-hidden="true"></span><h3><a href="{e(p["url"])}">{e(p["name"])}</a></h3>{home}{lic}</div>
          <p class="desc">{e(p["desc"])}</p>
          <div class="graph" role="img" aria-label="{p["total"]} commits, {unit} activity, {span}">{g}</div>
          <p class="meta"><span>{p["total"]} commits · last {fmt(p["last"].date())}</span><span>{unit}</span></p>
        </li>'''


more = f'\n      <p class="more"><a href="https://github.com/orgs/{ORG}/repositories">All repositories on GitHub →</a></p>'
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
print(f"{len(shown)} of {len(projects)} projects: " + ", ".join(f"{p['name']} ({graph(p)[0]})" for p in shown))
