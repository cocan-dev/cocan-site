# cocan-site

Static presentation site for https://cocan.dev. Plain HTML and CSS plus two
small inline scripts in `index.html`: the light/dark theme switch and the hero
background (a decorative canvas), and a few lines that show the activity
tooltips in the visitor's time zone. No build tools, no cookies, no
analytics, no third-party requests. The only thing stored is the theme choice
in the visitor's own browser (local storage). Hosted on GitHub Pages.

- Preview locally: `python -m http.server 8080` in this folder.
- The Open source cards are generated from the public repos of the cocan-dev
  org by `scripts/update_activity.py` (needs the GitHub CLI, `gh`).
- `.github/workflows/deploy.yml` runs that script and deploys the site on every
  push and once an hour. Nothing is committed back, so the cards in the
  committed `index.html` can be out of date; the live site is not.
- The workflow copies a fixed list of files. If you add or remove a file the
  site needs, change the `cp` line in `deploy.yml` in the same commit.
- Pages must use the "GitHub Actions" source in the repo settings.
- GitHub pauses scheduled workflows after 60 days without repo activity;
  re-enable it in the Actions tab if the cards stop updating.