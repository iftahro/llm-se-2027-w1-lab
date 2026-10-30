Name: Iftah Roichman
Date: 2026-10-29

# Exercise A - Execution findings

Execute your triage module on at least 20 issues from `data/snapshot/dev.json`. 
Look at the output. Write down anything that surprised you.

Runs, model `gemini/gemini-3.5-flash-lite`:

- Run 1: `uv run python -m triage.cli --split dev --limit 20 --show-gold`. 16 records, 4 failures (429).
- Run 2: `uv run python -m triage.cli --split dev --per-repo 7 --delay 5 --show-gold`. 21 records, 0 failures.
- Of the 21 issues in run 2, only 9 have a gold type, and 8 of those 9 match.

---
### Surprise 1

- **Input issue json**: run 2, all 21 issues.
- **Output triaged issue**: `confidence` is 0.90, 0.95 or 1.00 on every record; the lowest is 0.90.
- **What is surprising**: The one prediction that disagrees with gold (#3908, below) has confidence 0.90, the same as correct ones. Self-reported confidence carries almost no information, so any "confident enough" threshold in routing would pass everything.

---
### Surprise 2

- **Input issue json**: run 2, all 21 issues.
- **Output triaged issue**: every `bug` got severity `medium`, and every enhancement or documentation issue got `low`. No `critical` or `high` appeared in run 2; run 1 produced exactly one `high` (hono #4032).
- **What is surprising**: Severity just restates the type. It does not separate "Textual apps hang after resuming from sleep" (textual #5464) or "proxy middleware loses the response status code" (hono #3926) from a minor typing complaint. The rubric is in the prompt, but the model is not using it.

---
### Surprise 3

- **Input issue json**: hono #3908, "`Content-Type` header only works with `ctx.body()`", filed through the bug template ("What steps can reproduce the bug?"), labels `['enhancement']`.
- **Output triaged issue**: `{"issue_type": "bug", "severity": "low", "has_reproduction_steps": true, "confidence": 0.9, "gold_type": "enhancement"}`
- **What is surprising**: The only mismatch in run 2, and the gold label is arguably the wrong one: the reporter used the bug template and the maintainers relabelled it. "Gold" here means "what a maintainer decided", not "correct".

---
### Surprise 4

- **Input issue json**: textual #5426, "url returned by href parameter in LinkClicked is decoding when it should not (Markdown Widget)".
- **Output triaged issue**: `"summary": ": The Markdown widget incorrectly decodes URLs returned by the LinkClicked href parameter."`
- **What is surprising**: The summary starts with a stray `": "`, a leftover of the reply format. It passes validation, because validation checks only the length. "Reject anything invalid" only rejects what we thought to check.

---
### Surprise 5

- **Input issue json**: hono #3962, "Exporting Bun websocket gives a TypeScript error" (it concerns `hono/bun`, an adapter).
- **Output triaged issue**: `"component": "middleware"`, with 4 other hono issues in run 1 also given `middleware`.
- **What is surprising**: Hono's component list has only `middleware` and `testing`, so the model squeezes anything component-like into `middleware`. A two-item vocabulary invites over-assignment instead of `none`.

---
### Surprise 6

- **Input issue json**: run 2, all 21 issues.
- **Output triaged issue**: no record used `issue_type: "unknown"`, and no record was rejected by validation.
- **What is surprising**: Both safety valves we designed (the `unknown` type and reject-on-invalid) never fired on real data. They are only exercised by the mocked tests, so we cannot tell yet whether they work against this model.

---
### Surprise 7

- **Input issue json**: `data/snapshot/dev.json`, first 20 entries.
- **Output triaged issue**: all 20 were hono issues.
- **What is surprising**: The split is sorted by repo (80 hono, 80 litestar, 80 textual), so "the first 20 issues" never reached litestar or textual. Fixed with `--per-repo`.

---
### Surprise 8

- **Input issue json**: run 1, issues 17–20 (hono #4041, #4058, #4062, #4065).
- **Output triaged issue**: `model call failed: LMRateLimitError ... 429 You exceeded your current quota` on stderr; no records.
- **What is surprising**: The Gemini free tier allows about 15 calls a minute and asked for a 20-second wait; LiteLLM's 2 retries back off much faster than that, so they did not help. A batch of 20 fails without pacing (`--delay 5` fixed it).

---
### Surprise 9

- **Input issue json**: textual issues in run 2 (#5416 … #5464).
- **Output triaged issue**: 7 records, all with `gold_type: null`.
- **What is surprising**: None of the textual issues in the sample has a gold type, and 12 of the 21 issues overall have none, so most outputs cannot be scored at all. Textual is deliberately the low-supervision repo, but it means our "8 of 9 match" says nothing about textual.

---
### Surprise 10

- **Input issue json**: textual #5423, a request to capture the Enter key in a `DataTable`.
- **Output triaged issue**: `"issue_type": "enhancement", "has_reproduction_steps": true`
- **What is surprising**: "Reproduction steps" for a feature request. The field only makes sense for bugs, and the spec never says what it means for other types.


# Exercise B — Review findings

## Part 1 — found by reading

Record every problem you find in the released diff. One block per finding.
Add as many as you need. Do not delete the unused ones — an empty block is
information too.

**These lock at 1:13.** Once you start running the code, anything new goes in
part 2 instead. That boundary is the measurement: without it there is no way to
tell what reading caught from what the test runner caught.

Confidence: `certain` | `probable` | `uncertain`

---

### Finding 1

- **Location** (file:line): `tests/exercise_b/test_batch.py`
- **Confidence**: probable
- **What is wrong**: Batch tests only use valid model output and at most 1 issue.
- **Why it matters** (what breaks, for whom, when): Bad output (`"Critical"`, `"urgent"`) and real batches are never tested.
- **What would have caught this** (a test? a type? a review rule? nothing?): Tests with bad values and 2+ issues.

---

### Finding 2

- **Location** (file:line): `similarity.py:7`
- **Confidence**: certain
- **What is wrong**: `levenshtein_fast` is not in `pyproject.toml`; `type: ignore` hides it.
- **Why it matters** (what breaks, for whom, when): Any batch of 2+ issues crashes, yet CI is green.
- **What would have caught this** (a test? a type? a review rule? nothing?): Running the batch once; a test with 2+ issues.

---

### Finding 3

- **Location** (file:line): `similarity.py:19-20` (`blame_context`)
- **Confidence**: certain
- **What is wrong**: Issue title goes into a shell command with `shell=True`.
- **Why it matters** (what breaks, for whom, when): A malicious title runs commands on the machine.
- **What would have caught this** (a test? a type? a review rule? nothing?): Review rule: no untrusted text in a shell; a security linter.

---

### Finding 4

- **Location** (file:line): `router.py` (`route_raw`)
- **Confidence**: certain
- **What is wrong**: `route_raw` ignores `confidence` and `has_reproduction_steps`, unlike `route`.
- **Why it matters** (what breaks, for whom, when): Batch issues are routed by weaker rules than single issues.
- **What would have caught this** (a test? a type? a review rule? nothing?): A test comparing `route` and `route_raw` on the same input.

---

### Finding 5

- **Location** (file:line): `policy.py:54`, `router.py` (`route_raw`)
- **Confidence**: certain
- **What is wrong**: `ticket_priority` is a second name for severity.
- **Why it matters** (what breaks, for whom, when): Breaks the package's "one concept, one name" rule.
- **What would have caught this** (a test? a type? a review rule? nothing?): Reading `schema.py` during review.

---

## Part 2 — found by running

After `git apply`, `uv run pytest`, `uv run pyright` and the batch run.

### What the tooling found that I did not

- **Which tool** (pytest / pyright / running it):
- **What it showed**:
- **Would I have found this by reading?** (be honest):

### What I found by reading that the tooling did not

- 

### Anything the tooling reported that turned out not to be a problem

- 

---

## Scoring (fill in after the reveal)

| | part 1 (reading) | part 1 + part 2 |
|---|---|---|
| Seeded defects found | | |
| Seeded defects missed | | |
| False positives | | |

**Reading detection rate**: found / (found + missed) = ____%

**Combined detection rate**: found / (found + missed) = ____%

The gap between those two is not a measure of you. It is a measure of which
defects a machine can catch and which ones still need a person — and the
second group is the reason this course exists.

### One sentence: what did you miss, and why do you think you missed it?


