"""Report photos in images/cats/ that are not hung in any gallery wing.

The gallery wings (gallery/*.html) are hand-written, so a photo added
for a journal entry or profile stays out of the gallery until someone
hangs it. Run this from the repo root before committing photo work:

    python3 bin/check_gallery.py

Exit code 1 when something is unhung, so it can gate CI if wanted.
"""

import glob
import os
import re
import sys

os.chdir(os.path.join(os.path.dirname(__file__), ".."))

photos = {
    os.path.basename(p)
    for p in glob.glob("images/cats/*")
    if re.search(r"\.(jpe?g|png)$", p, re.I)
}

hung = set()
for wing in glob.glob("gallery/*.html"):
    hung |= set(re.findall(r'images/cats/([^"]+)"', open(wing, encoding="utf-8").read()))

unhung = sorted(photos - hung)
if unhung:
    print("Photos not hung in any gallery wing:")
    for p in unhung:
        print(f"  images/cats/{p}")
    print(f"\n{len(unhung)} unhung of {len(photos)} total. "
          "Add an .artwork figure (frame + placard) to the right wing, "
          "and bump the lobby's work count.")
    sys.exit(1)

print(f"All {len(photos)} photos are hung in a wing.")
