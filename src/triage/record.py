"""The triage record and the issue it is made from.

Both are validated at construction. A record that would carry a value outside
its allowed set is never built: pydantic raises, and the caller reports the
issue as failed instead (see docs/triage-spec.md, "Validation").
"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Repo = Literal["litestar", "hono", "textual"]
IssueType = Literal["bug", "enhancement", "documentation", "question", "unknown"]
Severity = Literal["critical", "high", "medium", "low"]

# Mirrors [repos.component_labels] in config/repos.toml. Per-repo on purpose:
# components are not comparable across repos. Textual keeps none.
COMPONENTS: dict[str, tuple[str, ...]] = {
    "litestar": ("openapi", "dto", "di", "testing", "cli"),
    "hono": ("middleware", "testing"),
    "textual": (),
}

MAX_SUMMARY_CHARS = 200


class TriageError(Exception):
    """The model call failed, or its reply could not become a valid record."""


class Issue(BaseModel):
    """The part of a GitHub issue that triage is allowed to see.

    Labels and gold fields are deliberately absent, so they cannot reach the
    model by accident.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    repo: Repo
    number: int
    title: str
    body: str = ""

    @field_validator("body", mode="before")
    @classmethod
    def _missing_body_is_empty(cls, value: object) -> object:
        # GitHub returns null for an issue opened with no description.
        return "" if value is None else value


class TriageRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    repo: Repo
    number: int
    issue_type: IssueType
    component: str | None
    severity: Severity
    has_reproduction_steps: bool
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=1, max_length=MAX_SUMMARY_CHARS)

    @model_validator(mode="after")
    def _component_belongs_to_repo(self) -> Self:
        if self.component is not None and self.component not in COMPONENTS[self.repo]:
            allowed = ", ".join(COMPONENTS[self.repo]) or "none"
            raise ValueError(
                f"component {self.component!r} is not valid for {self.repo} (allowed: {allowed})"
            )
        return self
