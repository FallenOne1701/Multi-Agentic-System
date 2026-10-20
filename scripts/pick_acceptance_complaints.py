"""One-off helper: sample 20 non-empty reviews + branch/advice fixtures."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWS_PATH = ROOT / "data" / "normalized_reviews.json"
OUT_PATH = ROOT / "tests" / "fixtures" / "complaints.json"

BRANCHES = [
    {
        "id": "branch_clean",
        "text": "Why was I charged an exit load on HDFC Large Cap Fund?",
    },
    {
        "id": "branch_miss",
        "text": "My equity delivery order for TCS failed with error code 500",
    },
    {
        "id": "branch_recurring",
        "text": "Brokerage and exit load fees are too high",
    },
    {
        "id": "branch_pii",
        "text": (
            "Why exit load on HDFC Large Cap? "
            "My PAN is ABCDE1234F and phone 9876543210"
        ),
    },
]

ADVICE = [
    {"id": "advice_redeem", "text": "Should I redeem HDFC Large Cap?"},
    {"id": "advice_good", "text": "Is this scheme good?"},
    {"id": "advice_returns", "text": "What returns should I expect?"},
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    reviews = json.loads(REVIEWS_PATH.read_text(encoding="utf-8"))
    candidates = [
        r
        for r in reviews
        if isinstance(r.get("text"), str) and r["text"].strip()
    ]
    rng = random.Random(args.seed)
    sample = rng.sample(candidates, k=min(args.count, len(candidates)))

    items: list[dict] = []
    for i, r in enumerate(sample, start=1):
        items.append(
            {
                "id": f"review_{i:02d}",
                "source_id": r.get("id"),
                "text": r["text"].strip(),
            }
        )
    items.extend(BRANCHES)
    items.extend(ADVICE)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(items, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(items)} fixtures to {args.out}")


if __name__ == "__main__":
    main()
