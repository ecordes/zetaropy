"""Email the select-readers list about new or updated journal entries.

Runs in GitHub Actions on every push that touches posts/ (see
.github/workflows/notify.yml), and can also be invoked manually for a
single post via workflow_dispatch.

Rules:
  - A post file ADDED in the push is always announced.
  - A post file MODIFIED in the push is announced only when some commit
    message in the push contains the token [notify] -- so typo fixes
    stay silent.

Mail goes out through the Mailgun HTTP API.

Configuration comes from the environment (GitHub secrets):
  MAILGUN_API_KEY   Mailgun private API key
  MAILGUN_DOMAIN    verified sending domain, e.g. mg.zetaropy.com
  MAILGUN_API_BASE  optional; set to https://api.eu.mailgun.net for the
                    EU region (default is the US endpoint)
  MAIL_FROM         optional From address; defaults to
                    "Zetaropy <journal@MAILGUN_DOMAIN>"
  MAIL_RECIPIENTS   comma-separated list; sent as BCC so readers never
                    see each other's addresses

Stdlib only, by design -- the API is plain form-encoded POST with
HTTP basic auth, so no mailgun SDK is needed.
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

SITE = "https://www.zetaropy.com"
NOTIFY_TOKEN = "[notify]"
DEFAULT_API_BASE = "https://api.mailgun.net"


def run(*cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def parse_post(path, ref):
    """Pull title, description, and date line out of a post's HTML,
    reading the file as it exists at the given commit."""
    html = run("git", "show", f"{ref}:{path}")

    def first(pattern, default=""):
        m = re.search(pattern, html, re.S)
        return re.sub(r"\s+", " ", m.group(1)).strip() if m else default

    title = first(r"<title>(.*?)</title>")
    title = re.sub(r"\s*—\s*Zetaropy\s*$", "", title)
    # Drop the shared "From the archive:" prefix; the email says what it is.
    title = re.sub(r"^From the archive:\s*", "", title, flags=re.I)
    title = title[:1].upper() + title[1:] if title else os.path.basename(path)

    description = first(r'name="description"\s+content="(.*?)"')
    date_line = first(r'<span class="eyebrow">(.*?)</span>')

    return {
        "title": title,
        "description": description,
        "date": date_line.title() if date_line else "",
        "url": f"{SITE}/posts/{os.path.basename(path)}",
    }


def changed_posts(base, head):
    """Return (new, updated) post paths between two commits."""
    if not base or set(base) == {"0"}:
        # First push to the branch or a history rewrite: nothing safe to diff.
        return [], []
    diff = run("git", "diff", "--name-status", f"{base}..{head}", "--", "posts/")
    new, updated = [], []
    for line in diff.splitlines():
        fields = line.split("\t")
        status, path = fields[0], fields[-1]   # renames list old, then new
        if not path.endswith(".html"):
            continue
        if status == "A":
            new.append(path)
        elif status == "M" or status.startswith("R"):
            updated.append(path)
    if updated:
        messages = run("git", "log", "--format=%B", f"{base}..{head}")
        if NOTIFY_TOKEN not in messages:
            updated = []
    return new, updated


def compose(new, updated, ref):
    """Build (subject, body) covering every announced post."""
    entries = [("New entry", p) for p in new] + [("Updated entry", p) for p in updated]
    posts = [(kind, parse_post(path, ref)) for kind, path in entries]

    if len(posts) == 1:
        kind, post = posts[0]
        subject = f"Zetaropy — {kind.lower()}: {post['title']}"
    else:
        subject = f"Zetaropy — {len(posts)} journal updates"

    lines = ["Hello,", ""]
    for kind, post in posts:
        lines.append(f"{kind} in the Zetaropy journal: {post['title']}")
        if post["date"]:
            lines.append(f"  {post['date']}")
        if post["description"]:
            lines.append(f"  {post['description']}")
        lines.append(f"  {post['url']}")
        lines.append("")
    lines.append(f"All entries: {SITE}/journal.html")
    lines.append("")
    lines.append("— Zetaropy")
    return subject, "\n".join(lines)


def send(subject, body, dry_run):
    recipients = [r.strip() for r in os.environ.get("MAIL_RECIPIENTS", "").split(",") if r.strip()]
    domain = os.environ.get("MAILGUN_DOMAIN", "").strip()
    sender = os.environ.get("MAIL_FROM", "").strip()
    if not sender and domain:
        sender = f"Zetaropy <journal@{domain}>"

    if dry_run:
        print(f"DRY RUN — would send to {len(recipients)} recipient(s)")
        print(f"From: {sender or '(unset)'}")
        print(f"Subject: {subject}")
        print()
        print(body)
        return

    if not recipients:
        sys.exit("MAIL_RECIPIENTS is empty; nothing to send to")

    api_key = os.environ.get("MAILGUN_API_KEY", "").strip()
    missing = [name for name, value in
               (("MAILGUN_API_KEY", api_key), ("MAILGUN_DOMAIN", domain)) if not value]
    if missing:
        sys.exit(f"Mailgun is not configured: {', '.join(missing)} not set")

    api_base = os.environ.get("MAILGUN_API_BASE", "").strip() or DEFAULT_API_BASE
    url = f"{api_base.rstrip('/')}/v3/{domain}/messages"

    # Readers go in BCC so they never see each other; To keeps headers tidy.
    fields = [("from", sender), ("to", sender), ("subject", subject), ("text", body)]
    fields += [("bcc", r) for r in recipients]

    request = urllib.request.Request(url, data=urllib.parse.urlencode(fields).encode())
    token = base64.b64encode(f"api:{api_key}".encode()).decode()
    request.add_header("Authorization", f"Basic {token}")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace").strip()
        sys.exit(f"Mailgun rejected the message (HTTP {exc.code}): {detail}")
    except urllib.error.URLError as exc:
        sys.exit(f"Could not reach Mailgun at {api_base}: {exc.reason}")

    print(f"Sent to {len(recipients)} recipient(s): {subject}")
    if payload.get("id"):
        print(f"Mailgun message id: {payload['id']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", help="commit before the push")
    ap.add_argument("--head", help="commit at the tip of the push")
    ap.add_argument("--post", help="announce one post file by name (manual mode)")
    ap.add_argument("--kind", choices=["new", "updated"], default="new")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.post:
        path = "posts/" + os.path.basename(args.post)
        if not path.endswith(".html"):
            path += ".html"
        ref = "HEAD"
        if not os.path.exists(path):
            sys.exit(f"no such post: {path}")
        new = [path] if args.kind == "new" else []
        updated = [path] if args.kind == "updated" else []
    else:
        if not (args.base and args.head):
            sys.exit("need --base and --head, or --post")
        ref = args.head
        new, updated = changed_posts(args.base, args.head)

    if not new and not updated:
        print("No posts to announce.")
        return

    subject, body = compose(new, updated, ref)
    send(subject, body, args.dry_run)


if __name__ == "__main__":
    main()
