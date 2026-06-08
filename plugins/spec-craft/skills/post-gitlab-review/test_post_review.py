#!/usr/bin/env python3
"""Offline tests for post_review.py — no network, no glab, nothing posted.

Run:  python3 -m unittest test_post_review -v   (from the skill directory)
"""

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import post_review as pr  # noqa: E402


class ParseMrUrl(unittest.TestCase):
    def test_gitlab_com(self):
        self.assertEqual(
            pr._parse_mr_url("https://gitlab.com/group/project/-/merge_requests/42"),
            ("gitlab.com", "group/project", "42"),
        )

    def test_self_hosted_subgroups_and_trailing_segment(self):
        self.assertEqual(
            pr._parse_mr_url("https://git.example.org/g/sub/proj/-/merge_requests/7/diffs"),
            ("git.example.org", "g/sub/proj", "7"),
        )

    def test_query_string(self):
        self.assertEqual(
            pr._parse_mr_url("https://gitlab.com/a/b/-/merge_requests/9?tab=overview"),
            ("gitlab.com", "a/b", "9"),
        )

    def test_not_an_mr_url(self):
        with self.assertRaises(ValueError):
            pr._parse_mr_url("https://gitlab.com/a/b/-/issues/9")


class ParseRemoteUrl(unittest.TestCase):
    def test_scp_like(self):
        self.assertEqual(
            pr._parse_remote_url("git@git.example.org:group/project.git"),
            ("git.example.org", "group/project"),
        )

    def test_scp_like_subgroups(self):
        self.assertEqual(pr._parse_remote_url("git@host:a/b/c.git"), ("host", "a/b/c"))

    def test_https(self):
        self.assertEqual(
            pr._parse_remote_url("https://gitlab.com/group/sub/project.git"),
            ("gitlab.com", "group/sub/project"),
        )

    def test_https_no_git_suffix(self):
        self.assertEqual(
            pr._parse_remote_url("https://gitlab.com/group/project"),
            ("gitlab.com", "group/project"),
        )

    def test_https_with_credentials(self):
        self.assertEqual(
            pr._parse_remote_url("https://oauth2:tok@git.example.org/g/p.git"),
            ("git.example.org", "g/p"),
        )

    def test_ssh_scheme_with_port(self):
        self.assertEqual(
            pr._parse_remote_url("ssh://git@git.example.org:2222/group/project.git"),
            ("git.example.org", "group/project"),
        )


class BuildPayload(unittest.TestCase):
    refs = {"base_sha": "B", "start_sha": "S", "head_sha": "H"}

    def test_new_line_matches_legacy_shape(self):
        # The common case must produce exactly the proven-working payload.
        p = pr._build_draft_payload(self.refs, {"path": "a.py", "line": 10, "body": "x"})
        self.assertEqual(
            p,
            {
                "note": "x",
                "position": {
                    "position_type": "text",
                    "base_sha": "B", "start_sha": "S", "head_sha": "H",
                    "new_path": "a.py", "old_path": "a.py", "new_line": 10,
                },
            },
        )

    def test_deleted_line_uses_old_line_only(self):
        pos = pr._build_draft_payload(self.refs, {"path": "a.py", "old_line": 5, "body": "x"})["position"]
        self.assertEqual(pos["old_line"], 5)
        self.assertNotIn("new_line", pos)

    def test_context_line_has_both(self):
        pos = pr._build_draft_payload(self.refs, {"path": "a.py", "line": 3, "old_line": 2, "body": "x"})["position"]
        self.assertEqual((pos["new_line"], pos["old_line"]), (3, 2))

    def test_renamed_file_keeps_old_path(self):
        pos = pr._build_draft_payload(self.refs, {"path": "new.py", "old_path": "old.py", "line": 3, "body": "x"})["position"]
        self.assertEqual((pos["new_path"], pos["old_path"]), ("new.py", "old.py"))

    def test_new_line_alias(self):
        pos = pr._build_draft_payload(self.refs, {"path": "a.py", "new_line": 8, "body": "x"})["position"]
        self.assertEqual(pos["new_line"], 8)

    def test_no_line_raises(self):
        with self.assertRaises(ValueError):
            pr._build_draft_payload(self.refs, {"path": "a.py", "body": "x"})


class DryRun(unittest.TestCase):
    def test_dry_run_posts_nothing(self):
        """--dry-run must never issue a mutating glab call, even offline."""
        calls = []

        def fake_glab(args, host, stdin=None):
            calls.append(args)
            raise RuntimeError("network disabled in test")

        orig = pr._run_glab
        pr._run_glab = fake_glab
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps([{"path": "a.py", "line": 1, "body": "hi"}]))
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                rc = pr.main(["--mr", "https://gitlab.com/g/p/-/merge_requests/1", "--dry-run"])
        finally:
            pr._run_glab = orig
            sys.stdin = old_stdin

        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("DRY RUN", out)
        self.assertIn("a.py", out)            # the payload was rendered
        self.assertIn("placeholder", out.lower())  # fell back gracefully with no refs
        mutating = [a for a in calls if "POST" in a or "DELETE" in a or "PUT" in a]
        self.assertEqual(mutating, [], f"dry-run issued mutating calls: {mutating}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
