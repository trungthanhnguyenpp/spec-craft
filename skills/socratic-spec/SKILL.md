---
name: socratic-spec
description: Socratic deep interview with mathematical ambiguity gating that turns a vague idea into a crystal-clear specification file. Use when the user says "interview me", "deep interview", "ask me everything", "don't assume", "I have a vague idea", "not sure exactly what I want", "ouroboros", "socratic", or asks for thorough requirements gathering before any code is written. Do not use for detailed/specific requests, single-line fixes, or when the user says "just do it" or already has a PRD.
argument-hint: "<idea or vague description>"
---

<Purpose>
Socratic-spec replaces a vague idea with a crystal-clear specification by asking targeted Socratic questions, exposing hidden assumptions, and measuring clarity across weighted dimensions. It refuses to crystallize the spec until ambiguity drops below the threshold (0.2). The only output is a spec file at `specs/{slug}.md` — this skill does not execute any implementation work.
</Purpose>

<Use_When>
- User has a vague idea and wants thorough requirements gathering before any execution
- User says "deep interview", "interview me", "ask me everything", "don't assume", "make sure you understand"
- User says "ouroboros", "socratic", "I have a vague idea", "not sure exactly what I want"
- User wants to avoid "that's not what I meant" outcomes
- Task is complex enough that jumping to code would waste cycles on scope discovery
- User wants mathematically-validated clarity before committing to anything
</Use_When>

<Do_Not_Use_When>
- User has a detailed, specific request with file paths, function names, or acceptance criteria — execute directly
- User wants a quick fix or single change
- User says "just do it" or "skip the questions" — respect their intent
- User already has a PRD or plan file — work from that instead
</Do_Not_Use_When>

<Why_This_Exists>
AI can build anything. The hard part is knowing what to build. Single-pass "what do you want?" expansion struggles with genuinely vague inputs because it asks for features instead of exposing assumptions. This skill applies Socratic methodology to iteratively expose assumptions and mathematically gate readiness, ensuring genuine clarity before any code is committed to.

Inspired by the [Ouroboros project](https://github.com/Q00/ouroboros), which demonstrated that specification quality is the primary bottleneck in AI-assisted development.
</Why_This_Exists>

<Execution_Policy>
- Ask ONE question at a time — never batch multiple questions
- Target the WEAKEST clarity dimension with each question
- Make weakest-dimension targeting explicit every round: name the weakest dimension, state its score/gap, and explain why the next question is aimed there
- Gather codebase facts via the built-in `Explore` agent BEFORE asking the user about them
- For brownfield confirmation questions, cite the repo evidence that triggered the question (file path, symbol, or pattern) instead of asking the user to rediscover it
- Score ambiguity after every answer — display the score transparently
- Keep prompt payloads budgeted: summarize or trim oversized initial context/history before composing question, scoring, or spec prompts
- If the user's initial context is oversized, create a concise prompt-safe summary first and wait for that summary before ambiguity scoring or question generation
- Do not crystallize the spec until ambiguity ≤ 0.2 OR the user explicitly opts for early exit
- Allow early exit with a clear warning if ambiguity is still above 0.2
- Challenge agents activate at specific round thresholds to shift perspective
- This skill produces ONLY a spec file — never invokes any execution skill, agent, or pipeline
</Execution_Policy>

<Steps>

## Phase 1: Initialize

1. **Parse the user's idea** from the invocation arguments / surrounding conversation.
2. **Detect brownfield vs greenfield**:
   - Spawn the built-in `Explore` agent (single quick query) to check whether the cwd has existing source code, package files, or git history relevant to the idea.
   - If source files exist AND the user's idea references modifying/extending something: **brownfield**
   - Otherwise: **greenfield**
3. **For brownfield**: Spawn the `Explore` agent to map the relevant codebase areas. Keep the result as `codebase_context` (cited paths/symbols/patterns) for use in later prompts.
4. **Normalize oversized initial context**:
   - Inspect the initial idea plus any pasted artifacts, logs, transcripts, or file excerpts for prompt-budget risk before generating the first question.
   - If the initial context is oversized or likely to crowd out downstream prompts, produce a concise prompt-safe summary that preserves intent, decisions, constraints, unknowns, cited files/symbols, and any explicit non-goals.
   - Treat the summary as the canonical `initial_idea`. Never paste raw oversized context into question-generation, ambiguity-scoring, or spec-crystallization prompts.
5. **Initialize an in-conversation interview record** (no persistence — held in working memory across this conversation only):

```
interview = {
  type: "greenfield" | "brownfield",
  initial_idea: "<prompt-safe initial-context summary or user input>",
  rounds: [],
  current_ambiguity: 1.0,
  threshold: 0.2,
  codebase_context: <cited paths/symbols or null>,
  challenge_modes_used: [],
  ontology_snapshots: []
}
```

6. **Announce the interview** to the user:

> Starting socratic-spec interview. I'll ask targeted questions to understand your idea thoroughly before producing a spec. After each answer I'll show the clarity score. We'll crystallize the spec once ambiguity drops below 20%.
>
> **Your idea:** "{initial_idea}"
> **Project type:** {greenfield|brownfield}
> **Current ambiguity:** 100% (we haven't started yet)

## Phase 2: Interview Loop

Repeat until `ambiguity ≤ 0.2` OR user opts for early exit:

### Step 2a: Generate Next Question

Build the question generation prompt with:
- The prompt-safe initial-context summary (if one was created), otherwise the user's original idea
- Prior Q&A rounds, trimmed or summarized to fit the prompt budget while preserving decisions, constraints, unresolved gaps, and ontology changes
- Current clarity scores per dimension (which is weakest?)
- Challenge agent mode (if activated — see Phase 3)
- Brownfield codebase context (if applicable), summarized to cited paths/symbols/patterns instead of raw dumps

If any prompt input is too large, summarize it first and continue from the summary. Do not ask the next question or score ambiguity from an over-budget raw transcript.

**Question targeting strategy:**
- Identify the dimension with the LOWEST clarity score
- Generate a question that specifically improves that dimension
- State, in one sentence before the question, why this dimension is now the bottleneck to reducing ambiguity
- Questions should expose ASSUMPTIONS, not gather feature lists
- If the scope is still conceptually fuzzy (entities keep shifting, the user is naming symptoms, or the core noun is unstable), switch to an ontology-style question that asks what the thing fundamentally IS before returning to feature/detail questions

**Question styles by dimension:**

| Dimension | Question Style | Example |
|-----------|---------------|---------|
| Goal Clarity | "What exactly happens when...?" | "When you say 'manage tasks', what specific action does a user take first?" |
| Constraint Clarity | "What are the boundaries?" | "Should this work offline, or is internet connectivity assumed?" |
| Success Criteria | "How do we know it works?" | "If I showed you the finished product, what would make you say 'yes, that's it'?" |
| Context Clarity (brownfield) | "How does this fit?" | "I found JWT auth middleware in `src/auth/` (pattern: passport + JWT). Should this feature extend that path or intentionally diverge from it?" |
| Scope-fuzzy / ontology stress | "What IS the core thing here?" | "You have named Tasks, Projects, and Workspaces across the last rounds. Which one is the core entity, and which are supporting views or containers?" |

### Step 2b: Ask the Question

Use `AskUserQuestion` with the generated question. Present it clearly with the current ambiguity context:

```
Round {n} | Targeting: {weakest_dimension} | Why now: {one_sentence_targeting_rationale} | Ambiguity: {score}%

{question}
```

Options should include contextually relevant choices plus a free-text option.

### Step 2c: Score Ambiguity

After receiving the user's answer, score clarity across all dimensions inline. Use the following self-prompt (treat as your own scoring rubric, target temperature-0.1-style consistency — same inputs should produce the same scores):

```
Given the following interview transcript for a {greenfield|brownfield} project, score clarity on each dimension from 0.0 to 1.0. If the initial context or transcript was summarized for prompt safety, score from that summary plus the preserved round decisions/gaps; do not re-expand raw oversized context.

Original idea or prompt-safe initial-context summary: {idea_or_initial_context_summary}

Transcript or prompt-safe transcript summary:
{all rounds Q&A or summarized transcript}

Score each dimension:
1. Goal Clarity (0.0-1.0): Is the primary objective unambiguous? Can you state it in one sentence without qualifiers? Can you name the key entities (nouns) and their relationships (verbs) without ambiguity?
2. Constraint Clarity (0.0-1.0): Are the boundaries, limitations, and non-goals clear?
3. Success Criteria Clarity (0.0-1.0): Could you write a test that verifies success? Are acceptance criteria concrete?
{4. Context Clarity (0.0-1.0): [brownfield only] Do we understand the existing system well enough to modify it safely? Do the identified entities map cleanly to existing codebase structures?}

For each dimension provide:
- score: float (0.0-1.0)
- justification: one sentence explaining the score
- gap: what's still unclear (if score < 0.9)

Also identify:
- weakest_dimension: the single lowest-confidence dimension this round
- weakest_dimension_rationale: one sentence explaining why it is the highest-leverage target for the next question

5. Ontology Extraction: Identify all key entities (nouns) discussed in the transcript.

{If round > 1, inject: "Previous round's entities: {prior_entities from latest ontology snapshot}. REUSE these entity names where the concept is the same. Only introduce new names for genuinely new concepts."}

For each entity provide:
- name: string (e.g., "User", "Order", "PaymentMethod")
- type: string (e.g., "core domain", "supporting", "external system")
- fields: string[] (key attributes mentioned)
- relationships: string[] (e.g., "User has many Orders")

Produce the result as a structured JSON-shaped block. Include an "ontology" key containing the entities array alongside the dimension scores.
```

**Calculate ambiguity:**

- Greenfield: `ambiguity = 1 - (goal × 0.40 + constraints × 0.30 + criteria × 0.30)`
- Brownfield: `ambiguity = 1 - (goal × 0.35 + constraints × 0.25 + criteria × 0.25 + context × 0.15)`

**Calculate ontology stability:**

- **Round 1 special case:** Skip stability comparison. All entities are "new". Set `stability_ratio = N/A`. If any round produces zero entities, set `stability_ratio = N/A` (avoids division by zero).
- For rounds 2+, compare with the previous round's entity list:
  - `stable_entities`: entities present in both rounds with the same name
  - `changed_entities`: entities with different names but the same `type` AND >50% field overlap (treated as renamed, not new+removed)
  - `new_entities`: entities in this round not matched to any previous entity
  - `removed_entities`: entities in the previous round not matched to any current entity
  - `stability_ratio`: (stable + changed) / total_entities (0.0–1.0; 1.0 = fully converged)

Renamed entities count toward stability — the concept persists even if the name shifted. Two entities with different names but the same `type` and >50% field overlap should be classified as "changed" (renamed), not as one removed and one added.

**Show your work:** Before reporting stability numbers, briefly list which entities were matched (by name or fuzzy) and which are new/removed. This lets the user sanity-check the matching.

Append the ontology snapshot (entities + stability_ratio + matching_reasoning) to `interview.ontology_snapshots`.

### Step 2d: Report Progress

After scoring, show the user:

```
Round {n} complete.

| Dimension | Score | Weight | Weighted | Gap |
|-----------|-------|--------|----------|-----|
| Goal | {s} | {w} | {s*w} | {gap or "Clear"} |
| Constraints | {s} | {w} | {s*w} | {gap or "Clear"} |
| Success Criteria | {s} | {w} | {s*w} | {gap or "Clear"} |
| Context (brownfield) | {s} | {w} | {s*w} | {gap or "Clear"} |
| **Ambiguity** | | | **{score}%** | |

**Ontology:** {entity_count} entities | Stability: {stability_ratio} | New: {new} | Changed: {changed} | Stable: {stable}

**Next target:** {weakest_dimension} — {weakest_dimension_rationale}

{score <= 0.2 ? "Clarity threshold met! Ready to crystallize the spec." : "Focusing next question on: {weakest_dimension}"}
```

### Step 2e: Threshold Decision Gate

When `ambiguity ≤ 0.2`, do NOT immediately crystallize. Use `AskUserQuestion` to ask:

> Clarity threshold reached (ambiguity: {score}%). What next?

Options:
- **Crystallize spec now** — write the spec to `specs/{slug}.md` and stop.
- **Refine further** — return to Phase 2 to ask more questions and reduce ambiguity further.
- **Show me the spec preview first** — produce a draft spec inline for review, then ask again whether to write or refine.

The user can call this skill again after the spec is written to refine further.

### Step 2f: Check Soft Limits (only when threshold not yet met)

- **Round 3+**: Allow early exit if user says "enough", "let's go", "build it"
- **Round 10**: Show soft warning: "We're at 10 rounds. Current ambiguity: {score}%. Continue or proceed with current clarity?"
- **Round 20**: Hard cap: "Maximum interview rounds reached. Proceeding with current clarity level ({score}%)."

## Phase 3: Challenge Agents

At specific round thresholds, shift the questioning perspective. Each mode is used ONCE, then return to normal Socratic questioning. Track usage in `interview.challenge_modes_used`.

### Round 4+: Contrarian Mode
Inject into the question generation prompt:
> You are now in CONTRARIAN mode. Your next question should challenge the user's core assumption. Ask "What if the opposite were true?" or "What if this constraint doesn't actually exist?" The goal is to test whether the user's framing is correct or just habitual.

### Round 6+: Simplifier Mode
Inject into the question generation prompt:
> You are now in SIMPLIFIER mode. Your next question should probe whether complexity can be removed. Ask "What's the simplest version that would still be valuable?" or "Which of these constraints are actually necessary vs. assumed?" The goal is to find the minimal viable specification.

### Round 8+: Ontologist Mode (if ambiguity still > 0.3)
Inject into the question generation prompt:
> You are now in ONTOLOGIST mode. Ambiguity is still high after 8 rounds, suggesting we may be addressing symptoms rather than the core problem. The tracked entities so far are: {current_entities_summary from latest ontology snapshot}. Ask "What IS this, really?" or "Looking at these entities, which one is the CORE concept and which are just supporting?" The goal is to find the essence by examining the ontology.

## Phase 4: Crystallize Spec

When the user picks **Crystallize spec now** (or hits hard cap / chooses early exit):

1. **Generate the specification** using the prompt-safe transcript. If the full transcript or initial context is too large, include the summary plus all concrete decisions, acceptance criteria, unresolved gaps, and ontology snapshots; never overflow the prompt with raw oversized context.
2. **Pick a slug**: kebab-case, ≤6 words, derived from the goal statement.
3. **Write to file**: `specs/{slug}.md`. Create the `specs/` directory at the repo root if it does not exist.
4. **Report** the file path back to the user. Do NOT invoke any other skill, agent, or execution mode. The user takes it from here.

Spec structure:

```markdown
# Socratic Spec: {title}

## Metadata
- Rounds: {count}
- Final Ambiguity Score: {score}%
- Type: greenfield | brownfield
- Generated: {ISO-8601 timestamp}
- Threshold: 0.2
- Initial Context Summarized: {yes|no}
- Status: {PASSED | BELOW_THRESHOLD_EARLY_EXIT}

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | {s} | {w} | {s*w} |
| Constraint Clarity | {s} | {w} | {s*w} |
| Success Criteria | {s} | {w} | {s*w} |
| Context Clarity | {s} | {w} | {s*w} |
| **Total Clarity** | | | **{total}** |
| **Ambiguity** | | | **{1-total}** |

## Goal
{crystal-clear goal statement derived from interview}

## Constraints
- {constraint 1}
- {constraint 2}

## Non-Goals
- {explicitly excluded scope 1}
- {explicitly excluded scope 2}

## Acceptance Criteria
- [ ] {testable criterion 1}
- [ ] {testable criterion 2}
- [ ] {testable criterion 3}

## Assumptions Exposed & Resolved
| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| {assumption} | {how it was questioned} | {what was decided} |

## Technical Context
{brownfield: relevant codebase findings from Explore agent — cited paths/symbols}
{greenfield: technology choices and constraints}

## Ontology (Key Entities)
Filled from the FINAL round's ontology extraction.

| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| {entity.name} | {entity.type} | {entity.fields} | {entity.relationships} |

## Ontology Convergence
| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|-------------|-----|---------|--------|----------------|
| 1 | {n} | {n} | - | - | - |
| 2 | {n} | {new} | {changed} | {stable} | {ratio}% |
| ... | ... | ... | ... | ... | ... |
| {final} | {n} | {new} | {changed} | {stable} | {ratio}% |

## Interview Transcript
<details>
<summary>Full Q&A ({n} rounds)</summary>

### Round 1
**Q:** {question}
**A:** {answer}
**Ambiguity:** {score}% (Goal: {g}, Constraints: {c}, Criteria: {cr})

...
</details>
```

After writing, end the conversation turn with a one-line note:

> Spec written to `specs/{slug}.md`. Ambiguity: {score}%. Re-run socratic-spec to refine further.

</Steps>

<Tool_Usage>
- Use `AskUserQuestion` for each interview question and the threshold decision gate — provides clickable UI with contextual options
- Use the built-in `Explore` agent (via the `Agent` tool with `subagent_type="Explore"`) for brownfield codebase exploration BEFORE asking the user about the codebase
- Use `Write` to save the final spec to `specs/{slug}.md`
- Challenge agent modes are prompt-injection adjustments to your own next-question generation, not separate agent spawns
- This skill MUST NOT invoke any other skill, execution agent, or pipeline. Crystallizing and writing the spec is the terminal action.
</Tool_Usage>

<Examples>
<Good>
Targeting weakest dimension:
```
Scores: Goal=0.9, Constraints=0.4, Criteria=0.7
Next question targets Constraints (lowest at 0.4):
"You mentioned this should 'work on mobile'. Does that mean a native app,
a responsive web app, or a PWA? And are there specific devices or OS versions
you need to support?"
```
Why good: Identifies the weakest dimension, explains why it is now the bottleneck, asks a specific question to improve it, and doesn't batch multiple topics.
</Good>

<Good>
Gathering codebase facts before asking:
```
[spawns Explore agent: "find authentication implementation"]
[receives: "Auth is in src/auth/ using JWT with passport.js"]

Question: "I found JWT authentication with passport.js in `src/auth/`.
For this new feature, should we extend the existing auth middleware or
create a separate authentication flow?"
```
Why good: Explored first, cited the repo evidence that triggered the question, then asked an informed confirmation question. Never asks the user what the code already reveals.
</Good>

<Good>
Threshold gate:
```
Ambiguity: 18% — threshold reached.

What next?
  [Crystallize spec now]
  [Refine further]
  [Show me the spec preview first]
```
Why good: Doesn't auto-crystallize; gives the user the choice to keep refining.
</Good>

<Good>
Early exit with warning:
```
User: "That's enough, just write it"
System: "Current ambiguity is 35% (threshold: 20%). Areas still unclear:
  - Success Criteria: 0.5 (How do we verify the search ranking algorithm works?)
  - Constraints: 0.6 (No performance targets defined yet)

Spec will be flagged BELOW_THRESHOLD_EARLY_EXIT. Continue?"
  [Yes, write spec anyway] [Ask 2-3 more questions] [Cancel]
```
Why good: Respects the user's desire to stop but transparently shows the risk and flags it in the spec metadata.
</Good>

<Bad>
Batching multiple questions:
```
"What's the target audience? And what tech stack? And how should auth work?
Also, what's the deployment target?"
```
Why bad: Four questions at once — causes shallow answers and makes scoring inaccurate.
</Bad>

<Bad>
Asking about codebase facts:
```
"What database does your project use?"
```
Why bad: Should have spawned the Explore agent. Never ask the user what the code already tells you.
</Bad>

<Bad>
Auto-crystallizing without the gate:
```
"Ambiguity hit 19%, writing the spec now."
```
Why bad: Skips the threshold decision gate. The user should explicitly choose to crystallize or refine further.
</Bad>

<Bad>
Invoking another skill or executor:
```
"Spec written. Now invoking autopilot to implement..."
```
Why bad: This skill is interview-only. Producing the spec file is the terminal action.
</Bad>
</Examples>

<Escalation_And_Stop_Conditions>
- **Threshold met (ambiguity ≤ 0.2)**: Show threshold decision gate; do not auto-crystallize.
- **Hard cap at 20 rounds**: Crystallize with whatever clarity exists, mark status as `BELOW_THRESHOLD_EARLY_EXIT` if ambiguity > 0.2.
- **Soft warning at 10 rounds**: Offer to continue or crystallize.
- **Early exit (round 3+)**: Allow with a warning if ambiguity > 0.2; mark spec as `BELOW_THRESHOLD_EARLY_EXIT`.
- **User says "stop", "cancel", "abort"**: Stop immediately. No spec is written unless the user confirms a partial crystallization.
- **Ambiguity stalls** (same score ±0.05 for 3 rounds): Activate Ontologist mode to reframe (if not yet used).
- **All dimensions ≥ 0.9**: Skip directly to the threshold decision gate.
- **Codebase exploration fails**: Proceed as greenfield, note the limitation in the spec's Technical Context section.
</Escalation_And_Stop_Conditions>

<Final_Checklist>
- [ ] Interview completed (ambiguity ≤ 0.2 OR user chose early exit)
- [ ] Oversized initial context/history was summarized before scoring or question generation
- [ ] Ambiguity score displayed after every round
- [ ] Every round explicitly named the weakest dimension and why it is the next target
- [ ] Challenge agents activated at correct thresholds (round 4 / 6 / 8) where applicable
- [ ] Threshold decision gate offered when ambiguity first dropped to ≤ 0.2
- [ ] Spec file written to `specs/{slug}.md`
- [ ] Spec includes: goal, constraints, non-goals, acceptance criteria, clarity breakdown, ontology, transcript
- [ ] Brownfield confirmation questions cited repo evidence before asking the user to decide
- [ ] Per-round ambiguity report includes Ontology row with entity count and stability ratio
- [ ] Spec includes Ontology (Key Entities) table and Ontology Convergence section
- [ ] No execution skill, agent, or pipeline was invoked — the spec file is the terminal output
</Final_Checklist>

<Advanced>
## Brownfield vs Greenfield Weights

| Dimension | Greenfield | Brownfield |
|-----------|-----------|------------|
| Goal Clarity | 40% | 35% |
| Constraint Clarity | 30% | 25% |
| Success Criteria | 30% | 25% |
| Context Clarity | N/A | 15% |

Brownfield adds Context Clarity because modifying existing code safely requires understanding the system being changed.

## Challenge Agent Modes

| Mode | Activates | Purpose | Prompt Injection |
|------|-----------|---------|-----------------|
| Contrarian | Round 4+ | Challenge assumptions | "What if the opposite were true?" |
| Simplifier | Round 6+ | Remove complexity | "What's the simplest version?" |
| Ontologist | Round 8+ (if ambiguity > 0.3) | Find essence | "What IS this, really?" |

Each mode is used exactly once, then normal Socratic questioning resumes.

## Ambiguity Score Interpretation

| Score Range | Meaning | Action |
|-------------|---------|--------|
| 0.0 – 0.1 | Crystal clear | Offer the gate immediately |
| ≤ 0.2 | Clear enough | Threshold decision gate |
| 0.2 – 0.35 | Some gaps | Continue interviewing |
| 0.35 – 0.6 | Significant gaps | Focus on weakest dimensions |
| 0.6 – 0.8 | Very unclear | May need reframing (Ontologist) |
| > 0.8 | Almost nothing known | Early stages, keep going |

## Refining an Existing Spec

To refine a spec that was already written, re-run socratic-spec. Reference the existing spec file in your idea ("refine specs/todo-app.md — I want to add offline support"). The skill treats it as new context for a fresh interview, and the new spec can be written to a new slug or overwrite the original at the user's choice.
</Advanced>
