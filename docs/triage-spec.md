# Triage spec — Exercise A

The brief: *"Build a tool that reads a GitHub issue and produces a structured
triage record, so that incoming issues can be routed automatically instead of
by hand."*

This file pins down what that sentence leaves open. Every choice made here
that the brief did not dictate is also one line in `docs/decisions.md`.

## Scope

One issue in, one triage record out. Routing (which queue, how fast) is the
next step and is **not** built here — the record only has to carry enough to
drive it.

## Input

An issue as it appears in `data/snapshot/{train,dev}.json`. Only these fields
are sent to the model:

| Field | Why |
|---|---|
| `repo` | the component vocabulary depends on it |
| `title` | |
| `body` | truncated to the first 8,000 characters |

Never sent to the model: `labels` and every `gold_*` field (they are the
answers), plus `state`, `comments`, dates and `author_association` (not
available for a freshly opened issue, which is what triage sees).

## Output: the triage record

| Field | Type | Values | Notes |
|---|---|---|---|
| `repo` | str | `litestar` \| `hono` \| `textual` | copied from input, not from the model |
| `number` | int | | copied from input |
| `issue_type` | enum | `bug` \| `enhancement` \| `documentation` \| `question` \| `unknown` | `unknown` when the issue does not clearly fit one |
| `component` | str \| null | the repo's list in `config/repos.toml`, or null | litestar: openapi, dto, di, testing, cli. hono: middleware, testing. textual: always null |
| `severity` | enum | `critical` \| `high` \| `medium` \| `low` | rubric below |
| `has_reproduction_steps` | bool | | true only for concrete steps or a runnable snippet |
| `confidence` | float | 0.0–1.0 | the model's confidence in `issue_type` |
| `summary` | str | one sentence, ≤ 200 chars | what the issue is about, in neutral words |

### Severity rubric

| Value | Meaning |
|---|---|
| `critical` | crash, data loss, security problem, or the framework unusable for many users, with no workaround |
| `high` | a core feature broken, workaround is hard or absent |
| `medium` | a feature misbehaves, a workaround exists |
| `low` | cosmetic, docs, questions, and feature requests |

### Validation after the model call

Any field outside its allowed values **rejects the whole record** — nothing is
silently corrected:

- `issue_type` not in the enum (note `unknown` *is* in the enum).
- `component` neither null nor in that repo's list (for textual, only null is valid).
- `severity` not in the enum.
- `confidence` not a number, or outside 0–1.
- `summary` empty or longer than 200 chars.

A rejected record is reported as a failure for that issue (see below), with
the field and the offending value. The model's output is never trusted to be
well-formed; the record type is.

## Failure handling

- The model call has a 30 s timeout, at most 2 retries, and `max_tokens=2048`
  (thinking models return nothing at 64).
- If the call still fails, the reply cannot be parsed, or a field fails
  validation, the tool reports the
  failure for that issue (stderr, non-zero exit for a single issue) instead of
  inventing a record. In a multi-issue run, one failure does not stop the rest.

## Command line

```
uv run python -m triage.cli --split dev --number 4780                  # one issue from the snapshot
uv run python -m triage.cli --file issue.json                          # one issue (or a list) from a file
uv run python -m triage.cli --split dev --limit 20                     # first 20 dev issues
uv run python -m triage.cli --split dev --per-repo 7 --delay 5         # 7 per repo, paced for the free tier
```

- The snapshot is sorted by repo, so `--limit` alone only sees hono; use
  `--per-repo` for a representative sample.
- `--delay` waits between model calls; the Gemini free tier allows about 15
  calls a minute.

- Prints the record as JSON on stdout.
- `--split test` is refused: the test split is sealed.
- With `--show-gold`, also prints `gold_type` next to the prediction, for
  eyeballing only. Gold labels are still never sent to the model.

## Model

Read from `LLM_MODEL` in `.env` (currently `gemini/gemini-3.5-flash-lite`).
All DSPy code lives in `src/triage/extract.py`, the one file where pyright's
unknown-type rules are relaxed.

## Security

Issue text is untrusted data written by strangers.

- It goes to the model only as a DSPy input field, never into the
  instruction text.
- It is never passed to a shell, `subprocess`, `eval`, or a file path.
- The model has no tools; its output is only parsed into the record and
  validated as above.

## Package layout

| File | Contents |
|---|---|
| `src/triage/record.py` | `Issue`, `TriageRecord`, the enums, `TriageError` |
| `src/triage/extract.py` | DSPy signature, model setup, call |
| `src/triage/cli.py` | the command line |
| `tests/triage/test_*.py` | offline tests; the model is DSPy's `DummyLM` |

## Done when

- `uv run pyright` reports 0 errors.
- `uv run pytest` passes without network access.
- The tool has been run over 20 dev issues and the surprises are written in
  `review-findings.md`.
