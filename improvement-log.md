# Improvement log

Every time the agent gets something wrong, it goes here. Not the fix — the
*failure*, classified.

This file runs for the whole semester. In W12 you will use it to show what
changed about how you work. That only works if it was written as things
happened, so write entries the day they occur. An improvement log
reconstructed from memory in week eleven is a creative writing exercise.

## The taxonomy

Classify every entry as exactly one of:

| Class | Meaning | Where the fix usually belongs |
|---|---|---|
| `capability` | the model could not do this | change the task, or the model |
| `context` | it could have, but did not know something | what the agent is given to read |
| `tool` | it lacked a way to act or to check | tooling |
| `spec` | the request was ambiguous and it guessed | the specification |
| `concept` | it used the wrong idea or the wrong name | the domain model |
| `bug` | ordinary defect, nothing AI-specific | the code |

The class matters more than the fix. Choosing between `context` and `spec`
forces you to say whether the agent lacked information or you did — and those
have different remedies.

---

## Entries

### E1

- **Date**: 2026-10-29
- **What happened**: The agent planned the review run as "the first 20 dev issues" without checking how `dev.json` is ordered. It is sorted by repo, so all 20 were hono and litestar/textual were never seen.
- **Class**: context
- **Evidence** (session log timestamp, commit, or file:line): run 1 output; `docs/triage-spec.md` originally said `--limit 20`.
- **What I did about it**: Added `--per-repo N` (`src/triage/cli.py`, `select`) and reran with 7 per repo.
- **Did it work?**: Yes; run 2 covered all three repos.

---

### E2

- **Date**: 2026-10-29
- **What happened**: The agent designed timeouts and retries (30 s, 2 retries) without knowing the Gemini free tier is about 15 calls a minute. Issues 17–20 of run 1 failed with 429; the retries back off far less than the 20 s Gemini asked for.
- **Class**: context
- **Evidence**: run 1 stderr, `LMRateLimitError ... retryDelay 18s–23s`.
- **What I did about it**: Added `--delay SECONDS` between calls; reran with `--delay 5`.
- **Did it work?**: Yes; run 2 had 21 of 21 records and no errors.

---

### E3

- **Date**: 2026-10-29
- **What happened**: During setup the agent recommended `gemini-3.8-flash` without testing a call. It was overloaded (503), DSPy retried silently, and `verify_env.py` appeared to hang for minutes. The next suggestion, `gemini-3.5-flash`, returned empty replies under the validator's 64-token limit because it is a thinking model.
- **Class**: context
- **Evidence**: session log, setup part; direct test calls showing 503 and `max_tokens=64` truncation.
- **What I did about it**: Tested each model with one call (timeout 30 s, no retries) before choosing; moved to `gemini-3.5-flash-lite`.
- **Did it work?**: Yes; `verify_env.py` passed all checks.

---

### E4

- **Date**: 2026-10-29
- **What happened**: The agent said I would get duplicate plugins from two marketplaces, then had to retract it: it did not actually know how Claude Code handles two plugins with the same name.
- **Class**: capability
- **Evidence**: session log, plugin setup part.
- **What I did about it**: Asked "are you sure?"; it separated what it knew from what it was guessing.
- **Did it work?**: Yes, once challenged. The lesson is to ask for evidence on confident claims.

---

### E5

- **Date**: 2026-10-29
- **What happened**: The agent's spec named the CLI `python -m triage` (a `__main__.py`), but it built `src/triage/cli.py`, which runs as `python -m triage.cli`. The spec and code disagreed until noticed.
- **Class**: bug
- **Evidence**: `docs/triage-spec.md`, "Command line" and "Package layout".
- **What I did about it**: Updated the spec to match the code.
- **Did it work?**: Yes.

---

### E6

- **Date**: 2026-10-29
- **What happened**: First version of the code failed `uv run pyright` with 2 strict-mode errors (an untyped JSON value in `cli.py`, DSPy's `history` typed as `list[Unknown]` in a test).
- **Class**: bug
- **Evidence**: first pyright run; `src/triage/cli.py` `load_file`, `tests/triage/test_extract.py` `last_prompt`.
- **What I did about it**: Typed the JSON value as `Any`; read `history` through `getattr`.
- **Did it work?**: Yes; 0 errors.

---

### E7

- **Date**: 2026-10-29
- **What happened**: The agent proposed the record fields and silently dropped `duplicate_candidate`, one of the five fields the dataset's `gold_*` columns point at. It was not raised as a choice or written in `docs/decisions.md` until I asked whether we had chosen all the fields.
- **Class**: spec
- **Evidence**: `docs/decisions.md` (first version had no duplicate_candidate line); `data/snapshot/MANIFEST.md` lists it.
- **What I did about it**: Asked why it was missing; recorded the decision and the reason.
- **Did it work?**: Yes, but only because I asked. Scope decisions need to be surfaced, not made silently.
