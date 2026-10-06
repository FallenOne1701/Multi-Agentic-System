from groww_support.ingress import redact


def test_redacts_pan():
    r = redact("My PAN is ABCDE1234F please help")
    assert "ABCDE1234F" not in r.redacted_text
    assert "[PAN]" in r.redacted_text
    assert "PAN" in r.pii_types


def test_redacts_phone_and_email():
    r = redact("Call me at 9876543210 or me@example.com")
    assert "9876543210" not in r.redacted_text
    assert "me@example.com" not in r.redacted_text
    assert "[PHONE]" in r.redacted_text
    assert "[EMAIL]" in r.redacted_text


def test_redacts_aadhaar_with_spaces():
    r = redact("Aadhaar 1234 5678 9012")
    assert "1234 5678 9012" not in r.redacted_text
    assert "[AADHAAR]" in r.redacted_text


def test_redacts_otp_labeled():
    r = redact("OTP 482913 expired")
    assert "482913" not in r.redacted_text
    assert "[OTP]" in r.redacted_text


def test_clean_complaint_unchanged():
    text = "Why was I charged an exit load on HDFC Large Cap Fund?"
    r = redact(text)
    assert r.redacted_text == text
    assert r.pii_types == []
