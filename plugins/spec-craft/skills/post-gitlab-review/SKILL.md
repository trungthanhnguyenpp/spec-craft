---
name: post-gitlab-review
description: Post code-review findings as inline comments on a GitLab merge request — staged as draft notes and published together as one cohesive review instead of scattered threads. Use whenever the user wants review comments on a GitLab MR (gitlab.com or any self-hosted GitLab, via the glab CLI): turning /review or /code-review findings into MR comments, or asking to "leave comments on", "annotate", or "post my review to" a merge request. Language- and project-agnostic.
---

# Post a GitLab MR review

Turn a set of review findings into inline comments on a GitLab MR, anchored to
exact lines, posted as **one review** — not N scattered comment threads.

Works against any GitLab host (gitlab.com or self-hosted); host and project are
read from the git remote, or from a full MR URL. `glab` must be installed and
authenticated for that host (`glab auth status`).

## Running the script

`post_review.py` ships next to this SKILL.md. `${CLAUDE_PLUGIN_ROOT}` is **not**
reliably expanded in skill-invoked Bash, so `{skill_dir}` below means *the
absolute path to the directory containing this SKILL.md* — substitute it before
running. Resolve it once (e.g. `dirname` of this file's path) and reuse it:

```bash
SKILL_DIR=/abs/path/to/plugins/spec-craft/skills/post-gitlab-review
python3 "$SKILL_DIR/post_review.py" --mr <url|iid> ...
```

## Why a script (don't hand-roll `glab api` for this)

Three rules are easy to get wrong and fail *silently*; `post_review.py` encodes
them so you don't rediscover them the hard way:

1. **Inline position needs a JSON body.** `glab api -f "position[new_path]=…"`
   bracket syntax is dropped on the floor — the note posts as a plain, non-inline
   comment with no error. The position must go in a JSON `--input` body.
2. **`--input` sets no content type.** Without `-H 'Content-Type: application/json'`
   the API returns HTTP 415.
3. **Inline comments are draft notes.** Create them via `…/draft_notes`, then
   `…/draft_notes/bulk_publish` so they land as a single review.

(Raw `curl` against self-hosted instances may fail with HTTP 000 from sandboxed
environments — go through `glab api`, which uses the authenticated host.)

## Workflow

1. **Resolve the MR.** Accept a full URL or a bare numeric iid. A bare iid
   resolves project + host from the git remote (`origin` by default; override
   with `--remote`).

2. **Gather findings.** From a prior `/review` or `/code-review`, or by analyzing
   the diff yourself. Each finding needs a repo-relative `path`, a `line` **in the
   MR head revision**, and a markdown `body` — see *Writing the comment body* for
   how to word it.

3. **Pin the line anchor.** `line` must exist on the new side of the MR head —
   confirm with `git show <head_sha>:<path>` (the head SHA is in the MR's
   `diff_refs`). To comment on a *deleted* line, use `old_line` instead of `line`
   (and `old_path` if the file was renamed). If GitLab can't map an anchor, the
   script warns that the note posted **UNANCHORED** — `--discard`, fix the line,
   re-run.

4. **Preview, then confirm.** Run with `--dry-run` to print the exact payloads
   without posting anything, and show the findings as a short table
   (file:line — severity — one-line gist). Posting to a real MR is outward-facing
   — get a nod first.

5. **Stage the drafts.** Pipe the findings JSON to the script:

   ```bash
   python3 "$SKILL_DIR/post_review.py" --mr <url|iid> <<'JSON'
   [
     {"path": "api/users/handler.go", "line": 142, "body": "**[High] N+1 query** …"},
     {"path": "web/src/Cart.tsx", "line": 88, "body": "**[Medium] missing null check** …"}
   ]
   JSON
   ```

   This stages draft notes and prints each anchor — it does **not** publish.

6. **Publish.** Default is stage-then-ask: after staging, ask the user, then run
   `--publish-only`. If the skill was invoked with a `--publish` flag (the
   `/code-review --fix` style), skip the question and pass `--publish` so it
   stages and publishes in one go.

   ```bash
   python3 "$SKILL_DIR/post_review.py" --mr <url|iid> --publish-only
   ```

## Writing the comment body

The body *is* the review — the anchor just puts it on the right line. Write each
one to be skimmed, not read. A reviewer scans a dozen comments; every extra
sentence is a tax on that.

- **Severity tag first** — `**[High|Medium|Low] <title>**`. It sets the reader's
  priority before they read a word.
- **State the issue, then why it matters** — one or two sentences. The *why* is
  what earns attention and buy-in; lead with it, before any how-to-fix.
- **Add a fix only when it isn't obvious** from the problem. Don't restate the
  code, and skip the preamble ("I noticed that…", "It looks like…").
- **One concern per comment.** A second point buried in the same note gets lost;
  give it its own anchor.
- **Length scales with severity** — a `[High]` bug earns a few lines, a `[Low]`
  nit earns one. Cut anything not load-bearing: a bloated comment buries its own
  point.

The aim is an observable target — skimmable, one concern, length matched to
severity — not "be brief," which a reader can take as "drop the context that made
the comment worth posting."

## Script reference

`post_review.py --mr <url|iid> [--remote origin] [--file findings.json]`

| Mode | Effect |
|------|--------|
| (default) | create draft notes from findings on stdin; do not publish |
| `--dry-run` | print the payloads that would be posted; touch nothing |
| `--publish` | create draft notes **and** bulk-publish as one review |
| `--publish-only` | publish existing drafts; reads no findings |
| `--discard` | delete all existing draft notes (abandon a staged review) |

Findings JSON (array). `path` + `body` are required, plus a line anchor:

| Field | Meaning |
|-------|---------|
| `path` | repo-relative path on the new side |
| `body` | markdown comment (lead with a severity tag) |
| `line` | line number on the new side (the usual case) |
| `old_line` | line on the old side — for comments on deleted lines |
| `old_path` | old path, if the file was renamed |

## Notes & limits

- One finding = one anchor. For a point spanning several files, anchor on the
  most representative line and enumerate the rest in the body.
- A failed draft aborts the run; drafts already staged stay unpublished — re-run
  with `--discard` to clear them, or `--publish-only` to ship what landed.
- Bodies are markdown; GitLab renders the same flavor as the MR UI.
- Self-test the script offline: from `{skill_dir}`, run
  `python3 -m unittest test_post_review` (no network, posts nothing).
