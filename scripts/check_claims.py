#!/usr/bin/env python3
"""Check that the site still keeps the promises made on /privacy.html and in the footer.

Fails (exit 1) if a page loads anything from another address, sets cookies, runs
analytics, sends data, or stores anything in the browser other than the "theme"
choice. Run by the deploy workflow before every deploy; the workflow also runs on
a schedule, so a broken promise sends a failure e-mail from GitHub.

    python3 scripts/check_claims.py            # files in this folder
    python3 scripts/check_claims.py --live URL # also check the live site's response headers
"""
import re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = sorted(ROOT.glob("*.html"))
CSS = sorted(ROOT.glob("*.css"))
problems = []


def bad(where, what):
    problems.append(f"{where}: {what}")


def external(url):
    return bool(re.match(r"(?i)(https?:)?//", url.strip()))


TRACKERS = r"google-analytics|googletagmanager|gtag\(|plausible|matomo|piwik|hotjar|clarity\.ms|fbq\(|facebook\.net|doubleclick|segment\.com|mixpanel|sentry|cloudflareinsights|fonts\.googleapis|fonts\.gstatic|cdn\.jsdelivr|unpkg\.com|cdnjs"
SENDERS = r"document\.cookie|\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|EventSource|new\s+Image\s*\(|sessionStorage|indexedDB|serviceWorker"

for page in PAGES:
    html = page.read_text(encoding="utf-8")
    name = page.name
    # things the browser loads: must be on the site itself
    for tag, attr in (("script", "src"), ("img", "src"), ("iframe", "src"), ("source", "src"), ("video", "src"),
                      ("audio", "src"), ("embed", "src"), ("object", "data"), ("link", "href"), ("form", "action")):
        for m in re.finditer(rf"<{tag}\b[^>]*?\b{attr}\s*=\s*[\"']([^\"']+)[\"']", html, re.I):
            if tag == "form":
                bad(name, "has a form")
            elif external(m.group(1)):
                bad(name, f"<{tag}> loads {m.group(1)} from another address")
    if re.search(r"<iframe|<form|<embed|<object", html, re.I):
        bad(name, "has an iframe, form, embed or object")
    if re.search(r"<meta[^>]+http-equiv=[\"']refresh", html, re.I):
        bad(name, "has a meta refresh")
    inline = "\n".join(re.findall(r"(?is)<script\b[^>]*>(.*?)</script>", html))
    for m in re.finditer(TRACKERS, html, re.I):
        bad(name, f"mentions a tracker or external service: {m.group(0)}")
    for m in re.finditer(SENDERS, inline, re.I):
        bad(name, f"script uses {m.group(0)} (may send or store data)")
    # browser storage: only the "theme" key is allowed
    keyvar_ok = re.search(r"\bk\s*=\s*[\"']theme[\"']", inline)
    for m in re.finditer(r"localStorage\.(?:get|set|remove)Item\(\s*([^,)]+)", inline):
        key = m.group(1).strip()
        if key not in ('"theme"', "'theme'") and not (key == "k" and keyvar_ok) and not (key == '"theme"'):
            bad(name, f"localStorage key {key} is not the theme choice")
    if re.search(r"localStorage\.(?:key|clear)\(|localStorage\[", inline):
        bad(name, "script reads localStorage in a way that is not the theme choice")

for css in CSS:
    text = css.read_text(encoding="utf-8")
    for m in re.finditer(r"url\(\s*[\"']?([^)\"']+)", text, re.I):
        if external(m.group(1)) or m.group(1).startswith("data:text/html"):
            bad(css.name, f"loads {m.group(1)} from another address")
    if re.search(r"@import", text, re.I):
        bad(css.name, "uses @import")
    if re.search(r"@font-face", text, re.I):
        bad(css.name, "loads a custom font (the page says system fonts only)")

# the live site: still served by GitHub Pages, and no cookies are set
if "--live" in sys.argv:
    url = sys.argv[sys.argv.index("--live") + 1]
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "claims-check"}), timeout=30) as r:
            h = {k.lower(): v for k, v in r.headers.items()}
            if "set-cookie" in h:
                bad(url, "the server sets a cookie")
            if "github.com" not in h.get("server", "").lower():
                bad(url, f"no longer served by GitHub Pages (Server: {h.get('server')}); update /privacy.html")
    except Exception as e:  # a network blip must not look like a broken promise
        print(f"warning: could not reach {url}: {e}")

if problems:
    print("PRIVACY CLAIMS BROKEN. The site says it has no cookies, no analytics and no third-party requests.")
    print("Fix the change, or update /privacy.html and the footer on purpose, before deploying.\n")
    for p in problems:
        print(" -", p)
    sys.exit(1)
print(f"claims ok: {len(PAGES)} pages, {len(CSS)} stylesheets checked")