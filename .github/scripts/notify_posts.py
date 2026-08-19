"""Email the select-readers list about new or updated journal entries.

Runs in GitHub Actions on every push that touches posts/ (see
.github/workflows/notify.yml), and can also be invoked manually for a
single post via workflow_dispatch.

Rules:
  - A post file ADDED in the push is always announced.
  - A post file MODIFIED in the push is announced only when some commit
    message in the push contains the token [notify] -- so typo fixes
    stay silent.

Configuration comes from the environment (GitHub secrets):
  MAIL_SERVER      SMTP host, e.g. smtp.gmail.com
  MAIL_PORT        587 for STARTTLS (default) or 465 for implicit TLS
  MAIL_USERNAME    SMTP login
  MAIL_PASSWORD    SMTP app password
  MAIL_FROM        From address (defaults to MAIL_USERNAME)
  MAIL_RECIPIENTS  comma-separated list; sent as BCC so readers never
                   see each other's addresses

Stdlib only, by design.
"""

import argparse
import os
import re
import smtplib
import subprocess
import sys
from email.message import EmailMessage

SITE = "https://www.zetaropy.com"
NOTIFY_TOKEN = "[notify]"


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
    sender = os.environ.get("MAIL_FROM") or os.environ.get("MAIL_USERNAME", "")

    if dry_run:
        print(f"DRY RUN — would send to {len(recipients)} recipient(s)")
        print(f"Subject: {subject}")
        print()
        print(body)
        return

    if not recipients:
        sys.exit("MAIL_RECIPIENTS is empty; nothing to send to")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = sender          # readers are BCC'd; To keeps headers tidy
    msg["Bcc"] = ", ".join(recipients)
    msg.set_content(body)

    server = os.environ["MAIL_SERVER"]
    port = int(os.environ.get("MAIL_PORT", "587"))
    username = os.environ["MAIL_USERNAME"]
    password = os.environ["MAIL_PASSWORD"]

    if port == 465:
        with smtplib.SMTP_SSL(server, port) as smtp:
            smtp.login(username, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(server, port) as smtp:
            smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(msg)
    print(f"Sent to {len(recipients)} recipient(s): {subject}")


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
