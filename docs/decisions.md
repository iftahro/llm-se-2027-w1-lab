# Unspecified decisions

The brief did not tell you everything. Every time you or your agent chose
something the brief did not specify, add a line here.

Examples of the kind of thing that counts: what fields the record has, what
happens to an issue with no clear type, how confident is confident enough,
what the output looks like when the model returns nothing usable.

You will need this list in W2, when we reconstruct the requirements this
build implicitly assumed. The comparison across the cohort is the lesson, so
write down what you actually decided, not what you think is the right answer.

---

- Record fields: repo, number, issue_type, component, severity, has_reproduction_steps, confidence, summary.
- duplicate_candidate is left out: it needs a comparison against other issues, which "one issue in, one record out" cannot do, and it has no gold labels; deferred to a later step.
- issue_type vocabulary is bug / enhancement / documentation / question, shared across all three repos; hono's "meta" type is dropped.
- An issue with no clear type gets issue_type = "unknown", not null and not a forced guess.
- component uses each repo's own list from config/repos.toml (not normalised across repos) or null; textual has no list, so only null is valid there.
- severity has four levels (critical / high / medium / low) defined by a written rubric; feature requests, docs and questions are always "low".
- Any field outside its allowed values rejects the whole record as an error for that issue; nothing is silently corrected.
- has_reproduction_steps is true only for concrete steps or a runnable snippet, not for a prose description of the problem.
- confidence is a 0.0–1.0 float, self-reported by the model, and refers to issue_type only.
- No confidence threshold is applied in triage; deciding what is "confident enough" is left to routing.
- summary is one neutral sentence, at most 200 characters.
- Only repo, title and body are sent to the model; labels, gold fields, state, comments, dates and author_association are withheld.
- The body is truncated to its first 8,000 characters.
- If the model call fails, its reply cannot be parsed, or a field fails validation, the tool reports an error for that issue instead of emitting a record.
- In a multi-issue run, one failed issue does not stop the others.
- Model calls use a 30 s timeout, at most 2 retries, and max_tokens 2048 (headroom for thinking models).
- The model answers "none" when no component applies, because DSPy returns optional fields as the string "None".
- component is lower-cased and stripped before validation; this is the only normalisation applied to model output.
- An issue with a null body is triaged with an empty body rather than rejected.
- --per-repo N samples the first N issues of each repo, because the snapshot is sorted by repo.
- --delay pauses between calls to stay under the free-tier rate limit; there is no automatic wait on 429.
- The model is whatever LLM_MODEL in .env says (gemini/gemini-3.5-flash-lite), chosen because the validator's 64-token check fails on thinking models.
- Output is JSON on stdout, one record per line for multi-issue runs.
- The CLI refuses --split test.
- --show-gold prints gold_type beside the prediction for review; gold is never sent to the model.
- Tests run offline against a stubbed model.
