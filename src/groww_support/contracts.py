from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, model_validator

SchemeId = Literal["large_cap", "mid_cap", "small_cap", "gold_fof", "silver_fof"]
ThemeId = Literal["other", "trading_charts", "money_movement", "reliability", "fees_brokerage"]
PatternSignal = Literal["one-off", "recurring", "rising"]
Disposition = Literal["reply", "escalate", "handoff", "refuse", "disagree"]
ReviewStatus = Literal["pass", "fail", "blocked"]
ReviewCheck = Literal["citation", "advice", "performance", "pii", "shape"]
Priority = Literal["P1", "P2", "P3"]
PiiType = Literal["PAN", "AADHAAR", "ACCOUNT", "PHONE", "EMAIL", "OTP"]
AgentName = Literal["facts", "pattern", "compliance", "orchestrator"]


class DateWindow(BaseModel):
    start: str
    end: str


class FactsResult(BaseModel):
    status: Literal["covered", "not_covered"]
    scheme_id: SchemeId | None = None
    section_title: str | None = None
    fact: str | None = None
    citation: str | None = None
    last_checked: str | None = None
    searched: list[str]

    @model_validator(mode="after")
    def _covered_requires_citation(self) -> "FactsResult":
        if self.status == "covered":
            if not self.fact or not self.citation or not self.last_checked or not self.scheme_id:
                raise ValueError("covered FactsResult requires fact, citation, last_checked, scheme_id")
        if self.status == "not_covered":
            if self.fact is not None or self.citation is not None:
                raise ValueError("not_covered FactsResult must null fact and citation")
        return self


class PatternResult(BaseModel):
    theme_id: ThemeId
    theme_name: str
    signal: PatternSignal
    count: int
    recent_count: int
    window: DateWindow
    recent_window: DateWindow


class ComplianceResult(BaseModel):
    flags: list[Literal["advice", "performance_claim", "pii"]]
    pii_types: list[PiiType]
    advice_refusal: bool
    redacted_text: str


class RoutingNote(BaseModel):
    team: str
    priority: Priority
    why: str


class OrchestratorOutput(BaseModel):
    reply: str
    last_checked: str | None
    citation: str | None
    disposition: Disposition
    disagreement: bool
    routing_note: RoutingNote


class ReviewerFailure(BaseModel):
    check: ReviewCheck
    detail: str


class ReviewerResult(BaseModel):
    status: ReviewStatus
    round: int = Field(ge=1, le=2)
    failures: list[ReviewerFailure] = Field(default_factory=list)


class AgentsFiredEntry(BaseModel):
    round: int
    kind: Literal["initial", "reviewer_rework", "refinement"]
    fired: list[AgentName]
    skipped: list[AgentName]


class SessionState(BaseModel):
    redacted_text: str
    pii_types: list[PiiType] = Field(default_factory=list)
    facts: FactsResult | None = None
    pattern: PatternResult | None = None
    compliance: ComplianceResult | None = None
    draft: OrchestratorOutput | None = None
    review: ReviewerResult | None = None
    advice_refusal: bool = False
    refinement_count: int = 0
    agents_fired: list[AgentsFiredEntry] = Field(default_factory=list)
    # raw user string is intentionally absent
