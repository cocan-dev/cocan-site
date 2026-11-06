# cocan-site

Static presentation site for https://cocan.dev. Plain HTML and CSS plus one
tiny script (`grid.js`, the hero grid). No build tools, no cookies, no
analytics, no third-party requests. Hosted on GitHub Pages.

- Preview locally: `python -m http.server 8080` in this folder.
- The Open source cards are generated from the public repos of the cocan-dev
  org by `scripts/update_activity.py` (needs the GitHub CLI, `gh`).
- `.github/workflows/deploy.yml` runs that script and deploys the site on every
  push and once an hour. Nothing is committed back, so the cards in the
  committed `index.html` can be out of date; the live site is not.
- Pages must use the "GitHub Actions" source in the repo settings.
