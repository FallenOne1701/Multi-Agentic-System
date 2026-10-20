from groww_support.contracts import FactsResult, OrchestratorOutput, RoutingNote
from groww_support.reviewer import review_draft, rewrite_draft


def test_uncited_factual_claim_fails():
    draft = OrchestratorOutput(
        reply="HDFC Large Cap charges 1% exit load within 1 year. Last checked 25-Jun-2026.",
        last_checked="25-Jun-2026",
        citation=None,
        disposition="reply",
        disagreement=False,
        routing_note=RoutingNote(team="Mutual fund support", priority="P3", why="one-off"),
    )
    result = review_draft(draft, facts=None, round=1)
    assert result.status == "fail"
    assert any(f.check == "citation" for f in result.failures)


def test_advice_language_fails():
    draft = OrchestratorOutput(
        reply=(
            "You may want to consider staying invested longer. "
            "Last checked 25-Jun-2026. "
            "Source: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
        ),
        last_checked="25-Jun-2026",
        citation="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        disposition="reply",
        disagreement=False,
        routing_note=RoutingNote(team="x", priority="P3", why="y"),
    )
    result = review_draft(draft, facts=None, round=1)
    assert any(f.check == "advice" for f in result.failures)


def test_raw_phone_in_draft_fails():
    draft = OrchestratorOutput(
        reply=(
            "We received your number 9876543210. Last checked 25-Jun-2026. "
            "Source: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
        ),
        last_checked="25-Jun-2026",
        citation="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        disposition="reply",
        disagreement=False,
        routing_note=RoutingNote(team="x", priority="P3", why="y"),
    )
    result = review_draft(draft, facts=None, round=1)
    assert any(f.check == "pii" for f in result.failures)


def test_clean_covered_draft_passes():
    citation = "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
    draft = OrchestratorOutput(
        reply=(
            f"HDFC Large Cap Fund Direct Growth charges an exit load of 1% "
            f"if redeemed within 1 year. Last checked 25-Jun-2026. Source: {citation}"
        ),
        last_checked="25-Jun-2026",
        citation=citation,
        disposition="escalate",
        disagreement=False,
        routing_note=RoutingNote(
            team="Fees and mutual fund ops",
            priority="P2",
            why="recurring fees_brokerage 136",
        ),
    )
    facts = FactsResult(
        status="covered",
        scheme_id="large_cap",
        section_title="Exit load",
        fact="Exit load of 1% if redeemed within 1 year",
        citation=citation,
        last_checked="25-Jun-2026",
        searched=["large_cap"],
    )
    result = review_draft(draft, facts=facts, round=1)
    assert result.status == "pass"


def test_rewrite_restores_citation_from_facts():
    citation = "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
    draft = OrchestratorOutput(
        reply="HDFC Large Cap charges 1% exit load within 1 year. Last checked 25-Jun-2026.",
        last_checked="25-Jun-2026",
        citation=None,
        disposition="reply",
        disagreement=False,
        routing_note=RoutingNote(team="Mutual fund support", priority="P3", why="one-off"),
    )
    facts = FactsResult(
        status="covered",
        scheme_id="large_cap",
        section_title="Exit load",
        fact="Exit load of 1% if redeemed within 1 year",
        citation=citation,
        last_checked="25-Jun-2026",
        searched=["large_cap"],
    )
    failed = review_draft(draft, facts=facts, round=1)
    assert failed.status == "fail"
    fixed = rewrite_draft(draft, facts=facts, failures=failed.failures)
    assert fixed.citation == citation
    assert citation in fixed.reply
    assert review_draft(fixed, facts=facts, round=2).status == "pass"


def test_round_two_still_failing_is_blocked():
    draft = OrchestratorOutput(
        reply="You may want to consider staying invested longer.",
        last_checked=None,
        citation=None,
        disposition="reply",
        disagreement=False,
        routing_note=RoutingNote(team="x", priority="P3", why="y"),
    )
    result = review_draft(draft, facts=None, round=2)
    assert result.status == "blocked"
    assert result.failures
