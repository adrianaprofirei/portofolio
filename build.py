#!/usr/bin/env python3
"""Build the static site into ./site from data/content.json and src/.

Standard library only:  python build.py
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT = ROOT / "site"
DATA = ROOT / "data" / "content.json"


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def rich(s: str) -> str:
    """Escape text, then turn **bold** into <b> and `code` into <code>."""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)


class Figures:
    """Numbers figures and tables in document order, like a printed report."""

    def __init__(self):
        self.fig = 0
        self.tab = 0

    def caption(self, text: str, table: bool = False) -> str:
        if table:
            self.tab += 1
            label = f"Table {self.tab}."
        else:
            self.fig += 1
            label = f"Figure {self.fig}."
        return f'<span class="fig-no">{label}</span> {esc(text)}'


# ---------------------------------------------------------------- pieces


def label_block(n: dict) -> str:
    sub = f'<span class="node-sub">{esc(n["sub"])}</span>' if n.get("sub") else ""
    return f'<span class="node-label">{esc(n["label"])}</span>{sub}'


def render_flow(flow: dict, figs: Figures) -> str:
    """A line diagram as an ordered list: boxes joined by drawn arrows."""
    d = flow["direction"]
    items = []
    nodes = flow["nodes"]
    for i, n in enumerate(nodes):
        shape = n.get("shape", "box")
        branch = ""
        if n.get("branch"):
            b = n["branch"]
            branch = (
                f'<span class="branch">'
                f'<span class="arrow arrow-branch" aria-hidden="true"><span class="arrow-label">{esc(b["edge"])}</span></span>'
                f'<span class="node node-dashed">{label_block(b)}</span>'
                f'</span>'
            )
        arrow = ""
        if i < len(nodes) - 1:
            lab = f'<span class="arrow-label">{esc(n["out"])}</span>' if n.get("out") else ""
            arrow = f'<span class="arrow" aria-hidden="true">{lab}</span>'
        cls = "step has-branch" if branch else "step"
        items.append(f'<li class="{cls}"><span class="node node-{shape}">{label_block(n)}</span>{branch}{arrow}</li>')
    return (
        f'<figure class="flow-fig flow-fig-{d}">'
        f'<div class="flow-scroll" tabindex="0" role="group" aria-label="Diagram, scrolls sideways">'
        f'<ol class="flow flow-{d}{" flow-has-branch" if any(n.get("branch") for n in nodes) else ""}">'
        f'{"".join(items)}</ol></div>'
        f'<figcaption>{figs.caption(flow["caption"])}</figcaption></figure>'
    )


def render_media(m: dict, figs: Figures, cls: str = "") -> str:
    ratio = f"aspect-ratio: {m['w']} / {m['h']}"
    if m["kind"] == "video":
        inner = (f'<video class="js-autoplay" src="{esc(m["src"])}" poster="{esc(m["poster"])}" '
                 f'width="{m["w"]}" height="{m["h"]}" style="{ratio}" muted loop playsinline controls '
                 f'preload="none" aria-label="{esc(m["alt"])}"></video>')
    else:
        inner = (f'<img src="{esc(m["src"])}" width="{m["w"]}" height="{m["h"]}" style="{ratio}" '
                 f'alt="{esc(m["alt"])}" loading="lazy" decoding="async">')
    return f'<figure class="media {cls}">{inner}<figcaption>{figs.caption(m["caption"])}</figcaption></figure>'


def slot(case: dict, name: str) -> dict | None:
    return next((m for m in case.get("media", []) if m.get("slot") == name), None)


def text_blocks(c: dict) -> str:
    if isinstance(c["built"], list):
        built = '<ul class="ruled">' + "".join(f"<li>{rich(x)}</li>" for x in c["built"]) + "</ul>"
    else:
        built = f'<p class="body">{rich(c["built"])}</p>'
    return (f'<h4 class="sub">The problem</h4><p class="body">{rich(c["problem"])}</p>'
            f'<h4 class="sub">What I built</h4>{built}')


def meta_block(c: dict) -> str:
    repo = c["repo"].replace("https://", "")
    note = f'<p class="note">{esc(c["note"])}</p>' if c.get("note") else ""
    return (f'<p class="stack-line"><span>Stack</span> {esc(c["stack"])}</p>'
            f'<p class="repo"><a href="{esc(c["repo"])}">{esc(repo)}</a></p>{note}')


def head_block(c: dict, kicker: bool = True) -> str:
    k = f'<p class="kicker">{esc(c["kicker"])}</p>' if kicker else ""
    return (f'{k}<h3 id="h-{c["id"]}" class="case-title">{esc(c["title"])}</h3>'
            f'<p class="dek">{esc(c["dek"])}</p>')


# ---------------------------------------------------------------- case layouts


def case_lead(c: dict, figs: Figures) -> str:
    """Text left, numbers table right, wide diagram underneath."""
    t = c["table"]
    rows = "".join(f'<tr><th scope="row">{esc(a)}</th><td>{esc(b)}</td></tr>' for a, b in t["rows"])
    table = (f'<aside class="span-8-5" aria-label="{esc(c["title"])} in numbers"><table class="numbers">'
             f'<caption>{figs.caption(t["caption"], table=True)}</caption><tbody>{rows}</tbody></table></aside>')
    return f"""
<article id="{c["id"]}" class="case case-lead" aria-labelledby="h-{c["id"]}">
  <div class="g"><div class="span-1-10">{head_block(c)}</div></div>
  <div class="g case-cols">
    <div class="span-1-6">{text_blocks(c)}{meta_block(c)}</div>
    {table}
  </div>
  {render_flow(c["flow"], figs)}
</article>"""


def case_split(c: dict, figs: Figures) -> str:
    """Side note and headline, wide recording, three columns, two staggered screenshots."""
    wide, left, right = slot(c, "wide"), slot(c, "left"), slot(c, "right")
    built = '<ul class="ruled">' + "".join(f"<li>{rich(x)}</li>" for x in c["built"]) + "</ul>"
    # render in reading order so figure numbers follow the page
    wide_html = render_media(wide, figs, "wide-media") if wide else ""
    flow_html = render_flow(c["flow"], figs)
    shots = ""
    if left and right:
        shots = (f'<div class="g shots">{render_media(left, figs, "span-1-7")}'
                 f'{render_media(right, figs, "span-8-5 stagger-96")}</div>')
    return f"""
<article id="{c["id"]}" class="case case-split" aria-labelledby="h-{c["id"]}">
  <div class="g head-split">
    <p class="aside-note span-1-3">{esc(c["aside"])}</p>
    <div class="span-4-9 head-main">{head_block(c)}</div>
  </div>
  {wide_html}
  <div class="g case-cols">
    <div class="span-1-4"><h4 class="sub">The problem</h4><p class="body">{rich(c["problem"])}</p>{meta_block(c)}</div>
    <div class="span-5-4"><h4 class="sub">What I built</h4>{built}</div>
    <div class="span-9-4">{flow_html}</div>
  </div>
  {shots}
</article>"""


def case_media_first(c: dict, figs: Figures) -> str:
    """Two tall, staggered media on the left, the text on the right, then diagram and strip."""
    t1, t2, strip = slot(c, "tall-1"), slot(c, "tall-2"), slot(c, "strip")
    tall = ""
    if t1:
        tall += render_media(t1, figs, "span-1-3 tall")
    if t2:
        tall += render_media(t2, figs, "span-4-3 tall stagger-128")
    return f"""
<article id="{c["id"]}" class="case case-media-first" aria-labelledby="h-{c["id"]}">
  <div class="g case-cols">
    {tall}
    <div class="span-8-5">{head_block(c)}<div class="after-dek">{text_blocks(c)}{meta_block(c)}</div></div>
  </div>
  {render_flow(c["flow"], figs)}
  {render_media(strip, figs, "strip") if strip else ""}
</article>"""


LAYOUTS = {"lead": case_lead, "split": case_split, "media-first": case_media_first}


# ---------------------------------------------------------------- page


def build() -> None:
    c = json.loads(DATA.read_text(encoding="utf-8"))
    site, ct = c["site"], c["contact"]
    figs = Figures()

    cases = "".join(LAYOUTS[x["layout"]](x, figs) for x in c["cases"])

    smaller = "".join(
        f'<li class="g"><h3 class="span-1-3">{esc(p["title"])}</h3>'
        f'<div class="span-4-5"><p>{rich(p["summary"])}</p><p class="small-stack">{esc(p["stack"])}</p></div>'
        f'<p class="span-9-4 small-links">'
        + "".join(f'<a href="{esc(l["href"])}">{esc(l["label"])}</a>' for l in p["links"])
        + "</p></li>"
        for p in c["smaller"]
    )
    about = "".join(f"<p>{rich(p)}</p>" for p in c["about"])
    stack = "".join(f"<div><dt>{esc(a)}</dt><dd>{esc(b)}</dd></div>" for a, b in c["stack"])
    contact_rows = "".join(
        f'<li><span>{esc(r["label"])}</span><a href="{esc(r["href"])}"'
        + (' download' if r.get("download") else "")
        + f'>{esc(r["text"])}</a></li>'
        for r in ct["rows"]
    )

    og_url = (site["url"].rstrip("/") + "/og.png") if site.get("url") else "og.png"
    canonical = f'<link rel="canonical" href="{esc(site["url"])}">' if site.get("url") else ""

    page = (SRC / "index.html").read_text(encoding="utf-8")
    for key, val in {
        "title": esc(site["title"]),
        "description": esc(site["description"]),
        "og_image": esc(og_url),
        "canonical": canonical,
        "name": esc(site["name"]),
        "location": esc(site["location"]),
        "positioning": esc(site["positioning"]),
        "proof_label": esc(site["proofLabel"]),
        "proof": rich(site["proof"]),
        "cases": cases,
        "smaller": smaller,
        "about": about,
        "stack": stack,
        "email": esc(ct["email"]),
        "contact_rows": contact_rows,
        "cv": esc(ct["cv"]),
    }.items():
        page = page.replace("{{" + key + "}}", val)
    for asset in ("styles.css", "main.js", "fonts/fonts.css"):
        v = hashlib.sha1((SRC / asset).read_bytes()).hexdigest()[:8]
        page = page.replace(f'"{asset}"', f'"{asset}?v={v}"')
    leftover = re.findall(r"\{\{\w+\}\}", page)
    if leftover:
        raise SystemExit(f"unfilled placeholders: {leftover}")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / "index.html").write_text(page, encoding="utf-8")
    for name in ("styles.css", "main.js", "favicon.svg", "og.png", "404.html"):
        shutil.copy2(SRC / name, OUT / name)
    for folder in ("media", "fonts"):
        shutil.copytree(SRC / folder, OUT / folder)
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    cv = ROOT / ct["cv"]
    if cv.exists():
        shutil.copy2(cv, OUT / ct["cv"])
    else:
        print(f"note: {ct['cv']} not found in the repo root; the Download CV link will 404 until it is added")

    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"built {OUT.relative_to(ROOT)}/  ({size/1024:.0f} KB total)")


if __name__ == "__main__":
    build()
