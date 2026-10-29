from typing import Any

import pytest
from pydantic import ValidationError

from triage.record import Issue, TriageRecord


def record_fields(**overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "repo": "litestar",
        "number": 1,
        "issue_type": "bug",
        "component": "openapi",
        "severity": "medium",
        "has_reproduction_steps": True,
        "confidence": 0.8,
        "summary": "Schema generation drops a field.",
    }
    return fields | overrides


class TestRecord:
    # --- valid records ---

    def test_valid_record_is_built(self) -> None:
        record = TriageRecord(**record_fields())
        assert record.component == "openapi"

    def test_unknown_type_is_a_valid_answer(self) -> None:
        assert TriageRecord(**record_fields(issue_type="unknown")).issue_type == "unknown"

    def test_no_component_is_valid(self) -> None:
        assert TriageRecord(**record_fields(component=None)).component is None

    # --- rejected records: nothing is silently corrected ---

    @pytest.mark.parametrize(
        "overrides",
        [
            {"issue_type": "feature"},
            {"severity": "urgent"},
            {"confidence": 1.5},
            {"confidence": -0.1},
            {"summary": ""},
            {"summary": "x" * 201},
            {"component": "middleware"},  # a hono component, not a litestar one
            {"repo": "textual", "component": "testing"},  # textual has no components
        ],
    )
    def test_out_of_range_field_rejects_record(self, overrides: dict[str, Any]) -> None:
        with pytest.raises(ValidationError):
            TriageRecord(**record_fields(**overrides))

    # --- issue input ---

    def test_issue_ignores_labels_and_gold_fields(self) -> None:
        issue = Issue.model_validate(
            {"repo": "hono", "number": "7", "title": "t", "body": "b", "labels": ["bug"], "gold_type": "bug"}
        )
        assert issue.model_dump() == {"repo": "hono", "number": 7, "title": "t", "body": "b"}

    def test_null_body_becomes_empty(self) -> None:
        assert Issue.model_validate({"repo": "hono", "number": 1, "title": "t", "body": None}).body == ""
