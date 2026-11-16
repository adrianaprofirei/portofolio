# Portfolio

Static personal site. No framework, no npm, no trackers. Python 3 (standard library only) renders
`data/content.json` into `site/`.

```
data/content.json   all content: hero numbers, projects, about, stack, contact
src/                page template, CSS, JS, self-hosted fonts, favicon, OG image, optimised media
build.py            renders the template + data into site/
tools/check_links.py  checks every local file, #anchor and external URL in site/
tools/og.html       source of src/og.png (screenshot it at 1200×630)
cv.pdf              copied to site/cv.pdf by the build
```

## Build and preview

```bash
python build.py
python -m http.server 8765 --directory site
python tools/check_links.py
```

## Add a project

- A smaller project: add an object to `smaller` in `data/content.json` (`title`, `summary`, `stack`, `links`).
- A case study: add an object to `cases`. `layout` picks one of three article layouts:
  `lead` (text and a numbers `table`, wide diagram below), `split` (side note, a `wide` recording,
  three columns, `left`/`right` screenshots) or `media-first` (`tall-1`/`tall-2` media beside the text,
  then a diagram and a `strip`). Media go in `media` with the matching `slot`. The diagram is `flow`:
  `direction` `row` or `column`, and `nodes` in order (`label`, optional `sub`, `shape: "decision"`,
  `out` for the label on the next arrow, `branch` for a side exit). `**bold**` works in text fields.
  Figures and tables are numbered automatically in page order.

Put media in `src/media/`. Convert GIFs to muted MP4 first, for example:

```bash
ffmpeg -i demo.gif -an -movflags +faststart -c:v libx264 -pix_fmt yuv420p -crf 26 -vf "scale=trunc(iw/2)*2:-2" demo.mp4
```

## Deploy

Push to `main` with GitHub Pages set to "GitHub Actions" (Settings → Pages). The workflow in
`.github/workflows/pages.yml` runs `build.py` and publishes `site/`. All paths are relative, so it works
at `username.github.io` and at `username.github.io/repo/`. Once the URL is known, put it in
`site.url` in `content.json` so the canonical link and absolute OG image URL are emitted.
