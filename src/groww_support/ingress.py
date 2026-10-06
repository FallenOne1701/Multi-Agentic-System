from __future__ import annotations
import re
from pydantic import BaseModel
from groww_support.contracts import PiiType


class IngressResult(BaseModel):
    redacted_text: str
    pii_types: list[PiiType]


_PAN = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")
_AADHAAR = re.compile(r"\b(\d{4}\s?\d{4}\s?\d{4})\b")
_EMAIL = re.compile(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
_PHONE = re.compile(r"\b([6-9]\d{9})\b")
_OTP = re.compile(r"(?i)\b(?:OTP|one[-\s]?time\s+password)\s*[:\-]?\s*(\d{4,8})\b")
_ACCOUNT = re.compile(
    r"(?i)\b(?:account|a/c|acct)\s*(?:no\.?|number|#)?\s*[:\-]?\s*(\d{9,18})\b"
)

_RULES: list[tuple[re.Pattern[str], PiiType, str]] = [
    (_PAN, "PAN", "[PAN]"),
    (_EMAIL, "EMAIL", "[EMAIL]"),
    (_OTP, "OTP", "[OTP]"),
    (_ACCOUNT, "ACCOUNT", "[ACCOUNT]"),
    (_PHONE, "PHONE", "[PHONE]"),
    (_AADHAAR, "AADHAAR", "[AADHAAR]"),
]


def redact(raw: str) -> IngressResult:
    text = raw
    found: list[PiiType] = []
    for pattern, pii_type, token in _RULES:
        if pattern.search(text):
            text = pattern.sub(token, text)
            if pii_type not in found:
                found.append(pii_type)
    return IngressResult(redacted_text=text, pii_types=found)
