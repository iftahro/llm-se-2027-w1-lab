"""Command line: triage one issue, or the first N issues of a snapshot split.

    uv run python -m triage.cli --split dev --number 4780
    uv run python -m triage.cli --file issue.json
    uv run python -m triage.cli --split dev --limit 20 --show-gold
    uv run python -m triage.cli --split dev --per-repo 7 --delay 5 --show-gold

Records go to stdout as JSON, one per line. Failures go to stderr, one per
issue, and make the exit status 1; they never stop the remaining issues.
"""

import argparse
import json
import os
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from triage.record import Issue, TriageError, TriageRecord

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = ROOT / "data" / "snapshot"
OPEN_SPLITS = ("train", "dev")  # test is sealed

Triage = Callable[[Issue], TriageRecord]


def load_split(split: str) -> list[dict[str, Any]]:
    if split not in OPEN_SPLITS:
        raise ValueError(f"split {split!r} is not allowed; the test split is sealed")
    with (SNAPSHOT_DIR / f"{split}.json").open(encoding="utf-8") as f:
        return json.load(f)


def load_file(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        data: Any = json.load(f)
    if isinstance(data, dict):
        return [data]
    return data


def select(
    raw: list[dict[str, Any]], number: int | None, limit: int | None, per_repo: int | None
) -> list[dict[str, Any]]:
    if number is not None:
        found = [item for item in raw if int(item["number"]) == number]
        if not found:
            raise ValueError(f"no issue #{number} in the input")
        return found
    if per_repo is not None:
        # The snapshot is sorted by repo, so a plain --limit only ever sees the first one.
        taken: dict[str, int] = {}
        picked: list[dict[str, Any]] = []
        for item in raw:
            repo = str(item["repo"])
            if taken.get(repo, 0) < per_repo:
                taken[repo] = taken.get(repo, 0) + 1
                picked.append(item)
        return picked
    return raw[:limit] if limit is not None else raw


def run(raw_issues: list[dict[str, Any]], triage: Triage, show_gold: bool, delay: float = 0.0) -> int:
    """Triage each issue; returns the number that failed."""
    failures = 0
    for position, raw in enumerate(raw_issues):
        if position and delay:
            time.sleep(delay)  # free-tier quotas are per minute
        issue = Issue.model_validate(raw)
        try:
            record = triage(issue)
        except TriageError as exc:
            failures += 1
            print(json.dumps({"repo": issue.repo, "number": issue.number, "error": str(exc)}), file=sys.stderr)
            continue
        out = record.model_dump()
        if show_gold:
            out["gold_type"] = raw.get("gold_type")  # for review only; never sent to the model
        print(json.dumps(out, ensure_ascii=False), flush=True)
    return failures


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="triage", description="Triage GitHub issues into structured records.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--split", choices=OPEN_SPLITS, help="read data/snapshot/<split>.json")
    source.add_argument("--file", type=Path, help="a JSON file holding one issue or a list of issues")
    pick = parser.add_mutually_exclusive_group()
    pick.add_argument("--number", type=int, help="triage only the issue with this number")
    pick.add_argument("--limit", type=int, help="triage only the first N issues")
    pick.add_argument("--per-repo", type=int, help="triage the first N issues of each repo")
    parser.add_argument("--show-gold", action="store_true", help="print gold_type beside each record")
    parser.add_argument("--delay", type=float, default=0.0, help="seconds to wait between model calls")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, triage: Triage | None = None) -> int:
    args = parse_args(argv)
    raw = load_split(args.split) if args.split else load_file(args.file)
    try:
        issues = select(raw, args.number, args.limit, args.per_repo)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if triage is None:
        from triage.extract import make_lm, triage_issue  # imports DSPy, which is slow

        load_dotenv(ROOT / ".env")
        lm = make_lm(os.environ["LLM_MODEL"])

        def triage_with_model(issue: Issue) -> TriageRecord:
            return triage_issue(issue, lm)

        triage = triage_with_model

    return 1 if run(issues, triage, args.show_gold, args.delay) else 0


if __name__ == "__main__":
    sys.exit(main())
