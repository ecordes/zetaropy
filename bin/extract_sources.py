"""One-off: split the existing hand-written pages into src/ sources.

Run once to migrate. It reads each committed page, keeps the part that
is genuinely that page's own -- its front matter and its <main> block --
and drops the chrome, which templates/ now supplies. For entries it goes
further and drops the page-header and article scaffold too, leaving just
the prose and figures.

Whatever a page can derive from its neighbours is replaced with the
placeholder the build fills in: the journal list, the home page's newest
few, and each gallery wing's work count.

    python3 bin/extract_sources.py

Then `python3 bin/build.py` must reproduce the pages byte for byte. That
round trip is the proof the migration lost nothing; if it does not come
back clean, this script is wrong, not the pages.

Kept in the repo as the record of how the migration was done. It is not
part of the normal workflow and should not need running again.
"""

import glob
import os
import re
import sys

os.chdir(os.path.join(os.path.dirname(__file__), ".."))

WINGS = ["zeta", "entropy", "paradox", "howl"]


def read(path):
    return open(path, encoding="utf-8").read()


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)


def grab(pattern, html, flags=re.S):
    m = re.search(pattern, html, flags)
    return m.group(1) if m else None


def block(lines, key):
    """Render a front-matter block scalar, preserving the author's wrapping."""
    body = "\n".join(f"  {l}" for l in lines)
    return f"{key}: >\n{body}\n"


def listing_blurbs(path):
    """The per-post blurb lines as written in a listing page."""
    out = {}
    for m in re.finditer(r'href="posts/([^"]+)".*?<p>\n(.*?)\n\s*</p>',
                         read(path), re.S):
        out[m.group(1)] = [l.strip() for l in m.group(2).splitlines() if l.strip()]
    return out


def extract_posts():
    journal, home = listing_blurbs("journal.html"), listing_blurbs("index.html")
    for path in sorted(glob.glob("posts/*.html")):
        name = os.path.basename(path)
        html = read(path)

        title = grab(r"<title>(.*?) — Zetaropy</title>", html)
        archive = "FROM THE ARCHIVE" in html
        if archive:
            title = re.sub(r"^From the archive:\s*", "", title, flags=re.I)
            title = title[:1].upper() + title[1:]

        h1 = grab(r"<h1>\s*(.*?)\s*</h1>", html)
        first, rest = h1.split("<br>", 1)
        rest = grab(r"<span>(.*?)\.</span>", rest)

        body = grab(r'<div class="post-body">\n(.*?)\n\s*</div>\n\s*'
                    r'<div class="post-footer">', html)
        # Written at 16 spaces because of where it sat in the page; a
        # source file has no such excuse, so pull it back to the margin.
        body = "\n".join(l[16:] if l.startswith(" " * 16) else l
                         for l in body.splitlines())

        description = re.sub(r"\s+", " ", grab(
            r'name="description"\s*\n\s*content="(.*?)"', html)).strip()

        meta = [f"title: {title}"]
        if archive:
            meta.append("archive: true")
        meta += [f"headline: {first.strip()}|{rest}",
                 f"description: {description}"]

        fm = "---\n" + "\n".join(meta) + "\n"
        fm += block(journal.get(name, []), "blurb")
        if name in home and home[name] != journal.get(name):
            fm += block(home[name], "blurb_home")
        fm += "---\n\n"

        write(f"src/posts/{name}", fm + body.strip("\n") + "\n")
        print(f"  src/posts/{name}")


def extract_pages():
    for path in sorted(glob.glob("*.html") + glob.glob("cats/*.html")
                       + glob.glob("gallery/*.html")):
        html = read(path)
        # Everything between the nav and the footer -- not just <main>,
        # since a page may carry a leading comment of its own.
        main = grab(r"^    </header>\n(.*?)\n^    <!-- Footer -->",
                    html, re.S | re.M).strip("\n")

        # Hand back to the build whatever it can work out for itself.
        if path == "journal.html":
            main = re.sub(r'(<div class="post-list">\n)\n.*?\n\n(\s*</div>)',
                          r"\1\n{{ post_list }}\n\n\2", main, flags=re.S)
        if path == "index.html":
            main = re.sub(r'(<div class="post-list embedded">\n)\n.*?\n\n(\s*</div>)',
                          r"\1\n{{ recent_posts }}\n\n\2", main, flags=re.S)
        if path == "gallery.html":
            for i, cat in enumerate(WINGS, start=1):
                main = main.replace(f"WING {i:02d} · "
                                    + grab(rf"WING {i:02d} · (\d+) WORKS", main)
                                    + " WORKS", f"WING {i:02d} · {{{{ works_{cat} }}}} WORKS")

        full = grab(r"<title>(.*?)</title>", html)
        short = grab(r"<title>(.*?) — Zetaropy</title>", html)
        meta = [f"title: {short}" if short else f"title_exact: {full}",
                "description: " + re.sub(r"\s+", " ", grab(
                    r'name="description"\s*\n\s*content="(.*?)"', html)).strip()]

        body_class = grab(r'<body class="(.*?)">', html)
        if body_class:
            meta.append(f"body_class: {body_class}")

        scripts = re.findall(r'<script src="(?:\.\./)?js/([\w.]+)"', html)
        if scripts != ["main.js"]:
            meta.append("scripts: " + " ".join(scripts))

        out = f"src/pages/{path}"
        write(out, "---\n" + "\n".join(meta) + "\n---\n\n" + main + "\n")
        print(f"  {out}")


if __name__ == "__main__":
    # A wing's own meta description carries its count too; let the build
    # own that number so it cannot drift from the placards.
    for cat in WINGS:
        p = f"gallery/{cat}.html"
        html = read(p)
        n = len(re.findall(r'class="placard-no"', html))
        write(p, html.replace(f"gallery: {n} works",
                              f"gallery: {{{{ works_{cat} }}}} works"))

    print("Extracting sources into src/ ...")
    extract_posts()
    extract_pages()

    for cat in WINGS:  # restore the served pages; build.py rewrites them
        os.system(f"git checkout -- gallery/{cat}.html 2>/dev/null")

    print("\nNow run: python3 bin/build.py --check")
