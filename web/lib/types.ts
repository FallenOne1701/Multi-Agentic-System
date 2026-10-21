export type PatternSignal = "one-off" | "recurring" | "rising";
export type Disposition =
  | "reply"
  | "escalate"
  | "handoff"
  | "refuse"
  | "disagree";
export type ReviewStatus = "pass" | "fail" | "blocked";
export type Priority = "P1" | "P2" | "P3";

export type DateWindow = { start: string; end: string };

export type FactsResult = {
  status: "covered" | "not_covered";
  scheme_id: string | null;
  section_title: string | null;
  fact: string | null;
  citation: string | null;
  last_checked: string | null;
  searched: string[];
};

export type PatternResult = {
  theme_id: string;
  theme_name: string;
  signal: PatternSignal;
  count: number;
  recent_count: number;
  window: DateWindow;
  recent_window: DateWindow;
};

export type ComplianceResult = {
  flags: Array<"advice" | "performance_claim" | "pii">;
  pii_types: string[];
  advice_refusal: boolean;
  redacted_text: string;
};

export type RoutingNote = {
  team: string;
  priority: Priority;
  why: string;
};

export type OrchestratorOutput = {
  reply: string;
  last_checked: string | null;
  citation: string | null;
  disposition: Disposition;
  disagreement: boolean;
  routing_note: RoutingNote;
};

export type ReviewerFailure = {
  check: string;
  detail: string;
};

export type ReviewerResult = {
  status: ReviewStatus;
  round: number;
  failures: ReviewerFailure[];
};

export type AgentsFiredEntry = {
  round: number;
  kind: "initial" | "reviewer_rework" | "refinement";
  fired: string[];
  skipped: string[];
};

export type SessionState = {
  redacted_text: string;
  pii_types: string[];
  facts: FactsResult | null;
  pattern: PatternResult | null;
  compliance: ComplianceResult | null;
  draft: OrchestratorOutput | null;
  review: ReviewerResult | null;
  advice_refusal: boolean;
  refinement_count: number;
  agents_fired: AgentsFiredEntry[];
};

export type SessionResponse = {
  id: string;
  session: SessionState;
};

export type ApproveResponse = {
  record_id: string;
  record_path: string;
  email_path: string;
};
