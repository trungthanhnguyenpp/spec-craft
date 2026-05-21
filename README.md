# spec-craft

A Claude Code plugin with two skills for turning vague ideas into clear specs and then into well-documented implementations.

## Skills

- **`socratic-spec`** — Deep Socratic interview that turns a vague idea into a crystal-clear specification file. Use when you want thorough requirements gathering before any code is written.
- **`implement-with-notes`** — Implements a spec while keeping a self-contained HTML log of decisions made outside the spec (deviations, tradeoffs, gotchas, open questions).

## Install

In Claude Code, run:

```
/plugin marketplace add trungthanhnguyenpp/spec-craft
/plugin install spec-craft
```

That's it — both skills are now available.

## Use

- `/socratic-spec` — start the interview
- `/implement-with-notes <spec>` — implement a spec with notes

## Updating

Plugins update through `/plugin` — run `/plugin marketplace update spec-craft` to pull the latest, then restart Claude Code if needed.
