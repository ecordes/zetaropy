"""Run every consistency check this site needs before a commit.

A served page still states things another page also states -- a wing's
work count appears on its lobby card and in its own meta description, an
entry appears in the journal list and in two neighbours' footers -- so
the failure mode here is never a crash, it is one page quietly
disagreeing with another.

Most of those are now derived by bin/build.py and cannot drift by hand,
which turns those checks into a regression test on the generator. The
two that still catch human mistakes are the unhung photo and the stale
build.

    python3 bin/check_site.py

Exits 1 listing everything wrong.
"""

import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402  (also chdirs us to the repo root)

WINGS = build.WINGS

# Deliberately NOT build.INDEX_KEEP: an independent copy is what makes
# the listings check an oracle on the generator rather than a tautology.
INDEX_KEEP = 3


def read(path):
    return open(path, encoding="utf-8").read()


def pages():
    """The built, served pages -- not src/ or templates/."""
    return sorted(glob.glob("*.html") + glob.glob("cats/*.html")
                  + glob.glob("gallery/*.html") + glob.glob("posts/*.html"))


def check_photos_hung():
    """Every photo in images/cats/ hangs in some gallery wing."""
    photos = {os.path.basename(p) for p in glob.glob("images/cats/*")
              if re.search(r"\.(jpe?g|png)$", p, re.I)}
    hung = set()
    for wing in glob.glob("gallery/*.html"):
        hung |= set(re.findall(r'images/cats/([^"]+)"', read(wing)))
    return [f"images/cats/{p} is not hung in any wing" for p in sorted(photos - hung)]


def check_wing_counts():
    """Placards, lobby card, and wing meta description all agree."""
    lobby = read("gallery.html")
    out = []
    for cat, num in WINGS:
        wing = read(f"gallery/{cat}.html")
        placards = len(re.findall(r'class="placard-no"', wing))
        m = re.search(rf"WING {num} · (\d+) WORKS", lobby)
        card = int(m.group(1)) if m else None
        m = re.search(r"gallery: (\d+) works", wing)
        meta = int(m.group(1)) if m else None
        if not (placards == card == meta):
            out.append(f"{cat} wing: {placards} placards, lobby says {card}, "
                       f"meta says {meta}")
    return out


def check_links():
    """Every local href/src resolves to a file that exists."""
    out = []
    for page in pages():
        base = os.path.dirname(page)
        for link in re.findall(r'(?:href|src)="([^"]+)"', read(page)):
            if link.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = link.split("#")[0].split("?")[0]
            if target and not os.path.exists(os.path.normpath(os.path.join(base, target))):
                out.append(f"{page}: broken link -> {link}")
    return out


def check_post_chain():
    """Prev/next footers agree with date order and point at real files."""
    posts = sorted(os.path.basename(p) for p in glob.glob("posts/*.html"))
    out = []
    for i, name in enumerate(posts):
        html = read("posts/" + name)
        m = re.search(r'<div class="post-footer">(.*?)</div>', html, re.S)
        if not m:
            out.append(f"posts/{name}: no post-footer block")
            continue
        hrefs = re.findall(r'href="([^"]+)"', m.group(1))
        if len(hrefs) != 2:
            out.append(f"posts/{name}: footer has {len(hrefs)} links, expected 2")
            continue
        nxt, prev = hrefs
        want_next = posts[i + 1] if i + 1 < len(posts) else None
        want_prev = posts[i - 1] if i > 0 else None
        if want_next and nxt != want_next:
            out.append(f"posts/{name}: next is {nxt}, date order says {want_next}")
        if want_prev and prev != want_prev:
            out.append(f"posts/{name}: prev is {prev}, date order says {want_prev}")
    return out


def check_listings():
    """journal.html lists every post; index.html shows the newest few."""
    posts = sorted((os.path.basename(p) for p in glob.glob("posts/*.html")),
                   reverse=True)
    out = []

    listed = re.findall(r'href="posts/([^"]+)"', read("journal.html"))
    for missing in set(posts) - set(listed):
        out.append(f"journal.html: {missing} is not listed")
    if listed != sorted(listed, reverse=True):
        out.append("journal.html: entries are not in newest-first order")

    front = re.findall(r'href="posts/([^"]+)"', read("index.html"))
    if front != posts[:INDEX_KEEP]:
        out.append(f"index.html: shows {front}, expected the newest "
                   f"{INDEX_KEEP}: {posts[:INDEX_KEEP]}")
    return out


def check_built():
    """The committed HTML is what src/ and templates/ currently produce,
    and nothing generated lingers after its source was deleted."""
    pages = build.build()
    return ([f"{p} is stale -- run: python3 bin/build.py"
             for p in build.stale_pages(pages)]
            + [f"{p} has no source -- run: python3 bin/build.py to remove it"
               for p in build.orphans(pages)])


# The last four can no longer drift by hand -- the build derives them --
# so they now serve as a regression test on the generator itself.
CHECKS = [
    ("photos hung in a wing", check_photos_hung),
    ("built HTML matches src/", check_built),
    ("local links resolve", check_links),
    ("wing counts agree", check_wing_counts),
    ("post prev/next chain", check_post_chain),
    ("journal and home listings", check_listings),
]

if __name__ == "__main__":
    failed = 0
    for label, fn in CHECKS:
        problems = fn()
        print(f"{'FAIL' if problems else ' ok '}  {label}")
        for p in problems:
            print(f"        {p}")
        failed += len(problems)

    print()
    print(f"{failed} problem(s)." if failed else "Everything agrees.")
    sys.exit(1 if failed else 0)
