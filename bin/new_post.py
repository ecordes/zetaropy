"""Start a journal entry: write its source file, then build.

There is nothing to wire up any more. The journal list, the newest few
on the home page, and the prev/next links on both neighbours are all
worked out by bin/build.py from the set of entries, so this only has to
put a source file in src/posts/ with sensible front matter.

    python3 bin/new_post.py "Matched from the start" \
        --blurb "Howl and Paradox, arriving together as kittens." \
        --date 2026-08-27 --archive

    --date      YYYY-MM-DD, defaults to today. A past date simply files
                the entry where it belongs.
    --blurb     one or two lines for the journal list
    --home      shorter blurb for the home page; defaults to --blurb
    --describe  <meta description>; defaults to --blurb
    --archive   tag it as an older story, like the other "early days" posts
    --h1        headline with | marking the line break, e.g.
                "Matched|from the start"; defaults to splitting at the
                middle word

Leaves a skeleton with a placeholder figure -- open it and write the
entry. bin/check_site.py fails while the placeholder is still in place.
"""

import argparse
import datetime as dt
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402  (also chdirs us to the repo root)

SKELETON = """<p class="lead">
    {lead}
</p>

<h2>First section</h2>

<p>
    Write the entry here. Ground every claim in what the photos
    actually show.
</p>

<figure>
    <img
        src="../images/cats/REPLACE.jpeg"
        alt="REPLACE with real alt text"
        width="1400"
        height="1050"
        loading="lazy"
    >
    <figcaption>
        A caption, wry and understated.
    </figcaption>
</figure>
"""


def wrap(text, width, indent=""):
    words, lines, line = text.split(), [], ""
    for w in words:
        if line and len(line) + 1 + len(w) > width:
            lines.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        lines.append(line)
    return f"\n{indent}".join(lines)


def main():
    p = argparse.ArgumentParser(description="Start a journal entry.")
    p.add_argument("title")
    p.add_argument("--date", default=dt.date.today().isoformat())
    p.add_argument("--blurb", default="")
    p.add_argument("--home", default="")
    p.add_argument("--describe", default="")
    p.add_argument("--archive", action="store_true")
    p.add_argument("--h1", default="")
    args = p.parse_args()

    try:
        date = dt.date.fromisoformat(args.date)
    except ValueError:
        sys.exit(f"--date must be YYYY-MM-DD, got {args.date!r}")

    blurb = args.blurb or args.title
    slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", args.title.lower())).strip("-")
    path = f"src/posts/{date.isoformat()}-{slug}.html"
    if os.path.exists(path):
        sys.exit(f"{path} already exists; delete it first or pick another title.")

    if args.h1 and "|" in args.h1:
        headline = args.h1
    else:
        # Split at the middle word; a one-word title stays whole and the
        # build renders it as a single emphasised line.
        words = (args.h1 or args.title).split()
        cut = len(words) // 2
        headline = (" ".join(words[:cut]) + "|" + " ".join(words[cut:])
                    if cut else words[0])

    meta = [f"title: {args.title}"]
    if args.archive:
        meta.append("archive: true")
    meta += [f"headline: {headline}",
             f"description: {args.describe or blurb}",
             "blurb: >\n  " + wrap(blurb, 54, "  ")]
    if args.home:
        meta.append("blurb_home: >\n  " + wrap(args.home, 50, "  "))

    open(path, "w", encoding="utf-8").write(
        "---\n" + "\n".join(meta) + "\n---\n\n"
        + SKELETON.format(lead=wrap(blurb, 58, "    ")))
    print(f"Wrote {path}")

    written, _ = build.write_pages(build.build())
    print(f"Built {len(written)} page(s): the entry, the listings, and its neighbours")
    print(f"\nNow write it: {path}")


if __name__ == "__main__":
    main()
