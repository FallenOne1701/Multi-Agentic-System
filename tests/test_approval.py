import pytest
from groww_support.approval import approve
from groww_support.contracts import ReviewerResult


@pytest.mark.asyncio
async def test_approve_writes_record_and_draft(tmp_path, data_dir):
    from groww_support.orchestrator import handle_complaint

    session = await handle_complaint(
        "Why was I charged an exit load on HDFC Large Cap Fund?", data_dir
    )
    assert session.review is not None
    if session.review.status != "pass":
        session.review = ReviewerResult(status="pass", round=1, failures=[])
    arts = approve(session, tmp_path)
    record_path = tmp_path / "support_records.jsonl"
    assert record_path.exists()
    line = record_path.read_text(encoding="utf-8")
    assert "ABCDE1234F" not in line
    assert arts.email_path.exists()
    email = arts.email_path.read_text(encoding="utf-8").lower()
    assert "mailto:" not in email
    assert "smtp" not in email


@pytest.mark.asyncio
async def test_blocked_cannot_approve(tmp_path, data_dir):
    from groww_support.orchestrator import handle_complaint

    session = await handle_complaint("Why exit load on HDFC Large Cap?", data_dir)
    session.review = ReviewerResult(status="blocked", round=2, failures=[])
    with pytest.raises(PermissionError, match="approve"):
        approve(session, tmp_path)
