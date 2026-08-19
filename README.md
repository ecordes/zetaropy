# zetaropy
A website for zeta and entropy

## Journal email notifications

A GitHub Action (`.github/workflows/notify.yml`) emails a private list
of readers when the journal changes:

- **New post pushed to `main`** → email goes out automatically.
- **Edited post** → silent, unless a commit message in the push
  contains `[notify]`.
- **Manual**: Actions tab → "Notify readers of journal entries" →
  Run workflow, naming the post. A `dry_run` option prints the email
  in the workflow log instead of sending it.

Recipients are BCC'd, so readers never see each other's addresses.

### One-time setup

Create an app password with your mail provider, then set the repo
secrets (run these yourself; the password prompt keeps it out of
shell history):

```bash
gh secret set MAIL_SERVER      --body "smtp.example.com"
gh secret set MAIL_PORT        --body "587"
gh secret set MAIL_USERNAME    --body "you@example.com"
gh secret set MAIL_PASSWORD                 # paste when prompted
gh secret set MAIL_FROM        --body "you@example.com"
gh secret set MAIL_RECIPIENTS  --body "a@example.com, b@example.com"
```

Port 587 uses STARTTLS; 465 uses implicit TLS. `MAIL_FROM` is
optional and defaults to `MAIL_USERNAME`.

To change the reader list later, re-run the `MAIL_RECIPIENTS` line
with the full new list (secrets can't be read back, only replaced).

To test end to end without emailing anyone: run the workflow manually
with `dry_run` checked, then read the composed email in the log.
