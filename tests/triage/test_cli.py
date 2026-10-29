import json
from pathlib import Path

import pytest

from triage.cli import load_split, main, select
from triage.record import Issue, TriageError, TriageRecord


def fake_triage(issue: Issue) -> TriageRecord:
    if issue.number == 2:
        raise TriageError("invalid model output: severity")
    return TriageRecord(
        repo=issue.repo,
        number=issue.number,
        issue_type="bug",
        component=None,
        severity="low",
        has_reproduction_steps=False,
        confidence=0.5,
        summary="A summary.",
    )


def write_issues(tmp_path: Path, numbers: list[int]) -> Path:
    path = tmp_path / "issues.json"
    issues = [{"repo": "hono", "number": n, "title": "t", "body": "b", "gold_type": "bug"} for n in numbers]
    path.write_text(json.dumps(issues), encoding="utf-8")
    return path


class TestCli:
    # --- output ---

    def test_prints_one_json_record_per_issue(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["--file", str(write_issues(tmp_path, [1, 3]))], triage=fake_triage) == 0
        lines = capsys.readouterr().out.splitlines()
        assert [json.loads(line)["number"] for line in lines] == [1, 3]

    def test_show_gold_adds_gold_type(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        main(["--file", str(write_issues(tmp_path, [1])), "--show-gold"], triage=fake_triage)
        assert json.loads(capsys.readouterr().out)["gold_type"] == "bug"

    def test_selects_by_number(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        main(["--file", str(write_issues(tmp_path, [1, 3])), "--number", "3"], triage=fake_triage)
        assert json.loads(capsys.readouterr().out)["number"] == 3

    def test_per_repo_takes_from_every_repo(self) -> None:
        raw = [{"repo": repo, "number": n} for repo in ("hono", "litestar", "textual") for n in range(5)]
        picked = select(raw, number=None, limit=None, per_repo=2)
        assert [(item["repo"], item["number"]) for item in picked] == [
            ("hono", 0), ("hono", 1), ("litestar", 0), ("litestar", 1), ("textual", 0), ("textual", 1)
        ]

    # --- failures ---

    def test_failed_issue_is_reported_and_others_continue(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["--file", str(write_issues(tmp_path, [1, 2, 3]))], triage=fake_triage) == 1
        captured = capsys.readouterr()
        assert [json.loads(line)["number"] for line in captured.out.splitlines()] == [1, 3]
        assert json.loads(captured.err)["number"] == 2

    def test_missing_number_is_an_error(self, tmp_path: Path) -> None:
        assert main(["--file", str(write_issues(tmp_path, [1])), "--number", "9"], triage=fake_triage) == 2

    # --- the sealed split ---

    def test_test_split_is_refused_by_cli(self) -> None:
        with pytest.raises(SystemExit):
            main(["--split", "test"], triage=fake_triage)

    def test_test_split_is_refused_by_loader(self) -> None:
        with pytest.raises(ValueError, match="sealed"):
            load_split("test")
