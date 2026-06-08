#!/usr/bin/env python3
"""Post GitLab MR review comments as inline draft notes, then publish as one review.

Works against any GitLab host (gitlab.com or self-hosted): the host and project
are read from the git remote, or parsed from a full MR URL.

Encodes the non-obvious `glab api` rules so they don't have to be rediscovered:
  - Inline position must be sent as a JSON body (`--input`); the `-f "position[...]"`
    bracket syntax is silently dropped and the note posts as a non-inline comment.
  - `--input` does NOT set a content type; without `-H 'Content-Type: application/json'`
    the API returns HTTP 415.
  - Inline comments are created as *draft notes*, then `bulk_publish`-ed so they land
    as a single review rather than N separate discussion threads.

Modes:
  (default)        create draft notes from findings, do NOT publish
  --dry-run        print the payloads that would be posted; touch nothing
  --publish        create draft notes AND bulk-publish them as one review
  --publish-only   bulk-publish whatever drafts already exist (no findings read)
  --discard        delete all existing draft notes (abandon a staged review)

Findings are read as a JSON array from stdin (or --file). Each finding needs a
`path` and a `body`, plus a line anchor:
  {"path": "<new-side path>", "line": <int>, "body": "<markdown>"}     # usual case
  {"path": "<path>", "old_line": <int>, "body": "..."}                 # deleted line
  {"path": "<new>", "old_path": "<old>", "line": <int>, "body": "..."} # renamed file

MR is given by --mr as either a full URL or a bare numeric iid (project/host then
come from the git remote named by --remote, default "origin").
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.parse

# Shown by --dry-run when the real diff_refs can't be fetched (offline / no auth),
# so a payload preview still works without a network round-trip.
PLACEHOLDER_REFS = {"base_sha": "<base_sha>", "start_sha": "<start_sha>", "head_sha": "<head_sha>"}


def _run_glab(args: list[str], host: str, stdin: str | None = None) -> str:
    cmd = ["glab", "api", "--hostname", host, *args]
    try:
        proc = subprocess.run(cmd, input=stdin, capture_output=True, text=True)
    except FileNotFoundError:
        raise RuntimeError(
            "glab CLI not found on PATH. Install it "
            "(https://gitlab.com/gitlab-org/cli) and run `glab auth login`."
        )
    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip()
        hint = f"  (try: glab auth login --hostname {host})" if ("401" in err or "403" in err) else ""
        raise RuntimeError(f"glab api failed ({proc.returncode}): {err}{hint}")
    return proc.stdout


def _parse_mr_url(url: str) -> tuple[str, str, str]:
    """Parse a full MR web URL into (host, project_path, iid). Pure."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.split("@")[-1]  # drop any embedded credentials
    path, sep, rest = parsed.path.partition("/-/merge_requests/")
    if not sep:
        raise ValueError(f"not an MR URL (no /-/merge_requests/): {url!r}")
    iid = rest.strip("/").split("/")[0]  # tolerate trailing /diffs, /commits, etc.
    project = path.strip("/")
    if not (host and project and iid):
        raise ValueError(f"could not parse host/project/iid from URL {url!r}")
    return host, project, iid


def _parse_remote_url(url: str) -> tuple[str, str]:
    """Parse a git remote URL into (host, project_path). Pure.

    Handles scp-like (git@host:group/project.git), https://, and ssh:// forms,
    with or without credentials, port, nested subgroups, or a .git suffix.
    """
    url = url.strip()
    if "://" in url:  # https:// or ssh://
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.split("@")[-1].split(":")[0]  # drop creds and :port
        project = parsed.path
    else:  # scp-like: [user@]host:group/project(.git)
        userhost, sep, project = url.partition(":")
        if not sep:
            raise ValueError(f"unrecognized remote URL: {url!r}")
        host = userhost.split("@")[-1]
    project = project.strip("/").removesuffix(".git")
    if not (host and project):
        raise ValueError(f"could not parse host/project from remote {url!r}")
    return host, project


def _resolve_mr(mr: str, remote: str) -> tuple[str, str, str]:
    """Return (host, url_encoded_project_path, iid)."""
    mr = mr.strip()
    if mr.startswith(("http://", "https://")):
        host, project, iid = _parse_mr_url(mr)
    else:
        iid = mr
        if not iid.isdigit():
            raise SystemExit(f"--mr must be an MR URL or a numeric iid, got {mr!r}")
        proc = subprocess.run(["git", "remote", "get-url", remote], capture_output=True, text=True)
        if proc.returncode != 0:
            raise SystemExit(
                f"could not read git remote {remote!r}: {proc.stderr.strip()} "
                "(run inside the repo, or pass a full MR URL)"
            )
        host, project = _parse_remote_url(proc.stdout.strip())
    return host, urllib.parse.quote(project, safe=""), iid


def _diff_refs(host: str, project: str, iid: str) -> dict:
    data = json.loads(_run_glab([f"projects/{project}/merge_requests/{iid}"], host))
    refs = data.get("diff_refs")
    if not refs:
        raise SystemExit("MR has no diff_refs (no diff to anchor against)")
    return refs


def _build_draft_payload(refs: dict, finding: dict) -> dict:
    """Build the draft-note request body for one finding. Pure.

    `line` (or `new_line`) anchors on the new side; `old_line` on the old side.
    Supplying both targets an unchanged context line. At least one is required.
    """
    new_line = finding.get("line", finding.get("new_line"))
    old_line = finding.get("old_line")
    if new_line is None and old_line is None:
        raise ValueError(f"finding needs `line` (new side) or `old_line` (deleted side): {finding}")
    new_path = finding["path"]
    position = {
        "position_type": "text",
        "base_sha": refs["base_sha"],
        "start_sha": refs["start_sha"],
        "head_sha": refs["head_sha"],
        "new_path": new_path,
        "old_path": finding.get("old_path", new_path),
    }
    if new_line is not None:
        position["new_line"] = int(new_line)
    if old_line is not None:
        position["old_line"] = int(old_line)
    return {"note": finding["body"], "position": position}


def _post_draft(host: str, project: str, iid: str, payload: dict) -> dict:
    out = _run_glab(
        ["-X", "POST", "-H", "Content-Type: application/json",
         f"projects/{project}/merge_requests/{iid}/draft_notes", "--input", "-"],
        host, stdin=json.dumps(payload),
    )
    return json.loads(out)


def _list_drafts(host: str, project: str, iid: str) -> list[dict]:
    return json.loads(_run_glab([f"projects/{project}/merge_requests/{iid}/draft_notes"], host))


def _validate(finding: dict) -> None:
    missing = {"path", "body"} - finding.keys()
    if missing:
        raise SystemExit(f"finding missing keys {missing}: {finding}")
    if finding.get("line") is None and finding.get("new_line") is None and finding.get("old_line") is None:
        raise SystemExit(f"finding needs a `line` (new side) or `old_line` (deleted side): {finding}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mr", required=True, help="MR URL or bare numeric iid")
    ap.add_argument("--remote", default="origin", help="git remote for project/host resolution (default: origin)")
    ap.add_argument("--file", help="findings JSON file (default: read stdin)")
    ap.add_argument("--dry-run", action="store_true", help="print payloads that would be posted; touch nothing")
    ap.add_argument("--publish", action="store_true", help="bulk-publish the drafts after creating them")
    ap.add_argument("--publish-only", action="store_true", help="publish existing drafts; read no findings")
    ap.add_argument("--discard", action="store_true", help="delete all existing draft notes and exit")
    args = ap.parse_args(argv)

    host, project, iid = _resolve_mr(args.mr, args.remote)
    base = f"projects/{project}/merge_requests/{iid}"

    if args.discard:
        drafts = _list_drafts(host, project, iid)
        for d in drafts:
            _run_glab(["-X", "DELETE", f"{base}/draft_notes/{d['id']}"], host)
        print(f"discarded {len(drafts)} draft note(s)")
        return 0

    if args.publish_only:
        _run_glab(["-X", "POST", f"{base}/draft_notes/bulk_publish"], host)
        print("published pending drafts as one review")
        return 0

    raw = open(args.file).read() if args.file else sys.stdin.read()
    findings = json.loads(raw)
    if not isinstance(findings, list) or not findings:
        raise SystemExit("findings must be a non-empty JSON array")
    for f in findings:
        _validate(f)

    if args.dry_run:
        try:
            refs = _diff_refs(host, project, iid)
        except Exception as e:  # offline / no auth — still show the payload shape
            refs = PLACEHOLDER_REFS
            print(f"(could not fetch diff_refs: {e}; showing payloads with placeholder SHAs)\n")
        print(f"DRY RUN — would POST {len(findings)} draft note(s) to {base}/draft_notes:\n")
        for f in findings:
            print(json.dumps(_build_draft_payload(refs, f), indent=2))
        print(f"\nNothing was posted. Drop --dry-run to stage these on MR !{iid}.")
        return 0

    refs = _diff_refs(host, project, iid)
    created = []
    for f in findings:
        note = _post_draft(host, project, iid, _build_draft_payload(refs, f))
        pos = note.get("position") or {}
        line = pos.get("new_line") or pos.get("old_line")
        if line is None:
            # GitLab accepted the note but couldn't map the position — it posted
            # unanchored. This is the silent failure this skill exists to surface.
            anchor = f.get("line") or f.get("new_line") or f.get("old_line")
            print(f"  ⚠ draft {note['id']} posted UNANCHORED — {f['path']}:{anchor} "
                  "may not exist on the MR head. --discard and fix the line.")
        else:
            print(f"  staged draft {note['id']} -> {pos.get('new_path') or pos.get('old_path')}:{line}")
        created.append(note["id"])

    print(f"\n{len(created)} draft note(s) staged on MR !{iid}.")
    if args.publish:
        _run_glab(["-X", "POST", f"{base}/draft_notes/bulk_publish"], host)
        print("published as one review.")
    else:
        print(f"Not published. To publish:  python3 {sys.argv[0]} --mr {args.mr} --publish-only")
        print(f"To abandon:                 python3 {sys.argv[0]} --mr {args.mr} --discard")
    return 0


if __name__ == "__main__":
    sys.exit(main())
