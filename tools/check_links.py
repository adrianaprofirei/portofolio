#!/usr/bin/env python3
"""Check every href/src/poster in site/*.html: local files, #anchors, and external URLs."""
import re, sys, urllib.request, urllib.error
from html.parser import HTMLParser
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"

class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.urls = []; self.ids = set()
    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k == "id": self.ids.add(v)
            if k in ("href", "src", "poster", "content") and v:
                if k == "content" and not v.endswith((".png", ".jpg")): continue
                self.urls.append((tag, k, v))

bad = 0
for page in sorted(SITE.glob("*.html")):
    p = P(); p.feed(page.read_text(encoding="utf-8"))
    seen = set()
    for tag, attr, url in p.urls:
        if url in seen: continue
        seen.add(url)
        if url.startswith("#"):
            ok = url[1:] in p.ids; msg = "anchor"
        elif url.startswith("mailto:"):
            ok = re.fullmatch(r"mailto:[^@\s]+@[^@\s]+\.\w+", url) is not None; msg = "mailto"
        elif url.startswith(("http://", "https://")):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (link-check)"})
                with urllib.request.urlopen(req, timeout=20) as r: code = r.status
            except urllib.error.HTTPError as e: code = e.code
            except Exception as e: code = repr(e)[:60]
            ok = code == 200; msg = f"HTTP {code}"
        else:
            path = url.split("?")[0].split("#")[0] or "index.html"
            target = SITE / path
            ok = target.is_file() or (target / "index.html").is_file(); msg = "file"
        print(f"{'ok ' if ok else 'BAD'}  {page.name:10} {msg:9} {url}")
        bad += not ok
print(f"\n{bad} problem(s)")
sys.exit(1 if bad else 0)
