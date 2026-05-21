---
name: implement-with-notes
description: Implement a spec while keeping docs/implementation-notes/<spec-slug>.html — a self-contained HTML log of decisions made outside the spec (deviations, tradeoffs, gotchas, open questions). Use on "/implement-with-notes <spec>" or when the user says "implement X and keep notes". Skip for trivial fixes or fully-explicit specs.
---

# Implement with Notes

Capture implementation decisions that aren't in the spec, in a persistent HTML doc beside the code. Micro-ADRs for in-flight work.

## Workflow

1. **Setup.** Slug the spec (kebab-case). Open or create `docs/implementation-notes/<spec-slug>.html` from `template.html`. Fill metadata: spec link, branch (`git branch --show-current`), today's date, status `in-progress`.

2. **Log inline.** After each meaningful change that meets the threshold below, append an entry at the top of `<main>` and bump `Last updated` **before moving on**. Don't batch — entries written days later lose the reasoning.

## Threshold

Log if any apply:
- Spec was silent or ambiguous and you picked an answer
- You deviated from what the spec said
- You picked one defensible option over another
- You hit a surprise (lib bug, doc mismatch, undocumented behavior)
- You left a TODO / hack / simplification for follow-up

Don't log: naming choices, formatting, routine refactors, obvious types.

**Rule of thumb:** *Would a thoughtful reviewer be surprised or push back?* If no, skip.

## Entry shape

```html
<article class="note" data-tag="TAG">
  <header class="note-header">
    <span class="tag tag-TAG">TAG_LABEL</span>
    <h2>One-line title</h2>
    <time>YYYY-MM-DD</time>
  </header>
  <section class="why"><h3>Why</h3><p>...</p></section>
  <section class="alternatives"><h3>Alternatives considered</h3><ul><li>...</li></ul></section>
  <section class="impact"><h3>Impact / What to watch</h3><p>...</p></section>
</article>
```

`Why` is required. Drop `alternatives` / `impact` sections if there's nothing real to say.

Tags: `deviation` · `tradeoff` · `gotcha` · `open-question`. The `data-tag` value and the `tag-*` CSS class must match (the filter dropdown depends on it).
