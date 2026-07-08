# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues. Repo inferred from `git remote -v` (currently `JubileeZ/FPL-Jubilee-Ascent`).

## Authentication — try in this order

**1. Reuse the stored Git credential (preferred, no install).** If `git push`/`pull` works, a credential helper already has a valid token. Retrieve it in-memory and call the REST API directly. Do NOT install anything first.

```bash
# bash / macOS / Linux
printf "protocol=https\nhost=github.com\n\n" | git credential fill
# → read the `password=` line; use it as `Authorization: Bearer <token>` against
#   https://api.github.com/repos/<owner>/<repo>/issues
```

```powershell
# Windows PowerShell (no printf; use here-string pipe)
$out = "protocol=https`nhost=github.com`n`n" | git credential fill 2>$null
$token = ($out | Select-String "^password=").Line.Substring("password=".Length)
$headers = @{ Authorization = "Bearer $token"; Accept = "application/vnd.github+json" }
Invoke-RestMethod -Uri "https://api.github.com/repos/<owner>/<repo>/issues" -Headers $headers
```

Verify before use: `GET /user` returns the login and `GET /repos/<owner>/<repo>` confirms `permissions.push`/`admin`.

**2. `gh` CLI** — only if step 1 yields no credential. `gh auth login` is interactive (browser/PAT), so the user must do it; agents cannot. Then use `gh issue ...` below.

**3. Ask the user for a PAT** — last resort; user handles creation/rotation.

### Cross-device notes

Credential helper and login method vary by machine — this is expected; step 1 works regardless:
- Windows: `manager-core` (Git Credential Manager), often an OAuth `gho_…` token.
- macOS: `osxkeychain`; may be `gho_…` (GCM) or a PAT.
- Linux: `libsecret`, `store`, or `cache`; usually a PAT.

Token type varies too (`gho_` OAuth, `ghp_` PAT, `github_pat_` fine-grained) — all work as `Bearer`. Don't assume a specific prefix or helper.

### Safety

- Never write the token to any file (repo or temp). Retrieve in-memory, use, drop.
- Don't echo the token in output. The `git credential fill` examples above print it to the controlling terminal only; capture into a variable before logging.
- If a token leaks into a terminal transcript, tell the user so they can rotate it.

## `gh` CLI reference (when available)

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

## REST API equivalents (when using the stored credential)

- **Create**: `POST /repos/<owner>/<repo>/issues` with JSON `{ "title", "body" }`.
- **Read**: `GET /repos/<owner>/<repo>/issues/<number>`.
- **List**: `GET /repos/<owner>/<repo>/issues?state=open`.
- **Comment**: `POST /repos/<owner>/<repo>/issues/<number>/comments` with `{ "body" }`.
- **Close**: `PATCH /repos/<owner>/<repo>/issues/<number>` with `{ "state": "closed" }`.
- **Labels**: `PATCH /repos/<owner>/<repo>/issues/<number>` with `{ "labels": ["..."] }`.

## When a skill says "publish to the issue tracker"

Create a GitHub issue — auth per the order above (stored credential first).

## When a skill says "fetch the relevant ticket"

`gh issue view <number> --comments`, or `GET /repos/<owner>/<repo>/issues/<number>` with the stored token.
