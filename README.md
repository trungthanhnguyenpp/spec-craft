# spec-craft

A Claude Code plugin with skills for turning vague ideas into clear specs, then into well-documented implementations, then into a tidy diff.

## Skills

- **`socratic-spec`** — Deep Socratic interview that turns a vague idea into a crystal-clear specification file. Use when you want thorough requirements gathering before any code is written.
- **`implement-with-notes`** — Implements a spec while keeping a self-contained HTML log of decisions made outside the spec (deviations, tradeoffs, gotchas, open questions).
- **`simplify`** — Reviews the current diff with three parallel agents (reuse, quality, efficiency), then fixes the findings directly. Use after writing code to tighten the diff before committing.
- **`post-gitlab-review`** — Posts code-review findings as inline comments on a GitLab MR, staged as draft notes and published together as one cohesive review. Works against gitlab.com or any self-hosted GitLab via the `glab` CLI.

## Install

In Claude Code, run:

```
/plugin marketplace add trungthanhnguyenpp/spec-craft
/plugin install spec-craft
```

That's it — all skills are now available.

## Use

- `/socratic-spec` — start the interview
- `/implement-with-notes <spec>` — implement a spec with notes
- `/simplify` — review and clean up the current diff
- `/post-gitlab-review` — post review findings as inline comments on a GitLab MR

## Updating

Plugins update through `/plugin` — run `/plugin marketplace update spec-craft` to pull the latest, then restart Claude Code if needed.
