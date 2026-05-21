# spec-craft

A pair of Claude Code skills for turning vague ideas into clear specs and then into well-documented implementations.

## Skills

- **`socratic-spec`** — Deep Socratic interview that turns a vague idea into a crystal-clear specification file. Use when you want thorough requirements gathering before any code is written.
- **`implement-with-notes`** — Implements a spec while keeping a self-contained HTML log of decisions made outside the spec (deviations, tradeoffs, gotchas, open questions).

## Install

Clone into your Claude Code skills directory:

```bash
git clone <repo-url> ~/Desktop/spec-craft
ln -s ~/Desktop/spec-craft/socratic-spec ~/.claude/skills/socratic-spec
ln -s ~/Desktop/spec-craft/implement-with-notes ~/.claude/skills/implement-with-notes
```

Or, if you prefer to keep skills directly under `~/.claude/skills/`, copy instead of symlink:

```bash
git clone <repo-url> /tmp/spec-craft
cp -r /tmp/spec-craft/socratic-spec ~/.claude/skills/
cp -r /tmp/spec-craft/implement-with-notes ~/.claude/skills/
```

Symlinks are recommended — they let you `git pull` updates and have them apply immediately.

## Use

In Claude Code:

- `/socratic-spec` — start the interview
- `/implement-with-notes <spec>` — implement a spec with notes
