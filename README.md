# zetaropy
A website for zeta and entropy

## Journal email notifications

A GitHub Action (`.github/workflows/notify.yml`) emails a private list
of readers when the journal changes:

- **New post pushed to `main`** → email goes out automatically.
- **Edited post** → silent, unless a commit message in the push has a
  line consisting of exactly `[notify]`. It must be a line of its own —
  merely mentioning the token in prose does not count.
- **Manual**: Actions tab → "Notify readers of journal entries" →
  Run workflow, naming the post. A `dry_run` option prints the email
  in the workflow log instead of sending it.

Recipients are BCC'd, so readers never see each other's addresses.

Delivery goes through the [Mailgun](https://www.mailgun.com) HTTP API.
The script is stdlib-only — no SDK to install.

### One-time setup

In Mailgun: add a sending domain (or use the sandbox domain for
testing) and complete its DNS verification, then copy the private API
key from Settings → API keys.

Then set the repo secrets (run these yourself; the prompt keeps the
key out of shell history):

```bash
gh secret set MAILGUN_API_KEY                  # paste when prompted
gh secret set MAILGUN_DOMAIN   --body "mg.zetaropy.com"
gh secret set MAIL_FROM        --body "Zetaropy <journal@mg.zetaropy.com>"
gh secret set MAIL_RECIPIENTS  --body "a@example.com, b@example.com"
```

`MAIL_FROM` is optional — it defaults to
`Zetaropy <journal@MAILGUN_DOMAIN>`. The address must be on the
Mailgun domain, or Mailgun will reject the message.

If your Mailgun account is in the EU region, also set:

```bash
gh secret set MAILGUN_API_BASE --body "https://api.eu.mailgun.net"
```

Two Mailgun gotchas worth knowing:

- A **sandbox** domain only delivers to *authorized recipients* (up to
  five, each confirmed by clicking a link in an invite email). Fine
  for a first test; a verified domain is needed for a real list.
- A verified domain needs its DNS records in place, or sends fail with
  a "domain not allowed to send" error. That error text is printed
  straight into the workflow log.

To change the reader list later, re-run the `MAIL_RECIPIENTS` line
with the full new list (secrets can't be read back, only replaced).

To test end to end without emailing anyone: run the workflow manually
with `dry_run` checked, then read the composed email in the log.
