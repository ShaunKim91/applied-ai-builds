"""A fictional fraud-pattern taxonomy for Verity's "fraud-signal
highlighting" feature.

Explicitly a fixed, admin-static Python list (not DB-editable, not a real
SIU-validated taxonomy) — every pattern name and description here is
invented for this demo. A match is always surfaced as "possible signal —
not a determination, route to SIU for review", never as a fraud verdict:
this module can only ever raise a flag for a human to look at, never make
or imply an actual finding.

Matching is keyword-only — deterministic and easy to audit. An earlier
version of this module also fell back to embedding cosine similarity
(`intfloat/multilingual-e5-small`) for a paraphrased description with no
exact keyword hit, but that was removed after being measured, not assumed,
to be unreliable for this domain: a completely unrelated question
("How quickly must Fenwick Mutual pay an undisputed claim in Cedermoor?")
scored 0.80-0.82 cosine similarity against EVERY fraud pattern description,
and even a generic weather sentence scored 0.74-0.78 — all comfortably
above any threshold that also caught real paraphrased positives (which
scored 0.77-0.89, overlapping the false-positive range entirely). This
embedding model's similarity tracks topical/domain adjacency ("this is
insurance-claims text"), not the specific factual match a fraud signal
needs — for this feature specifically, a keyword-only check that never
fires on an unrelated query is more useful than one that "sounds smart" but
flags nearly everything, since a compliance tool that cries wolf on every
query trains its own users to ignore it. See debug/ for the full write-up.
"""

FRAUD_PATTERNS = [
    {
        "id": "staged-collision",
        "label": "Possible staged-collision indicator",
        "description": "Multiple unrelated claimants in one low-speed collision with disproportionately severe soft-tissue injury claims and a shared, hard-to-verify witness.",
        "keywords": ["staged", "low-speed", "soft tissue", "shared witness", "phantom passenger"],
    },
    {
        "id": "inflated-contractor-invoice",
        "label": "Possible inflated-contractor-invoice pattern",
        "description": "A repair estimate significantly above regional norms from a contractor with a recent pattern of similarly inflated invoices across unrelated claims.",
        "keywords": ["inflated estimate", "duplicate invoice", "above market rate", "repeat contractor"],
    },
    {
        "id": "phantom-vehicle",
        "label": "Possible phantom-vehicle claim",
        "description": "A hit-and-run claim naming an unidentified vehicle with no corroborating police report, camera footage, or third-party witness.",
        "keywords": ["hit and run", "unidentified vehicle", "no police report", "no witness"],
    },
    {
        "id": "post-binding-loss",
        "label": "Possible post-binding-loss timing pattern",
        "description": "A reported loss date suspiciously close after a policy's effective/binding date, especially for a high-value claim.",
        "keywords": ["shortly after binding", "new policy", "immediately after coverage began"],
    },
    {
        "id": "duplicate-claim-ring",
        "label": "Possible duplicate-claim-ring pattern",
        "description": "The same loss, vehicle, or property appears across multiple claims filed under different claimant names within a short window.",
        "keywords": ["duplicate claim", "same vehicle", "same address", "multiple claimants"],
    },
]


def check(text: str) -> list[dict]:
    lowered = text.lower()
    hits = []
    for pattern in FRAUD_PATTERNS:
        if any(kw in lowered for kw in pattern["keywords"]):
            hits.append({"id": pattern["id"], "label": pattern["label"], "matched_by": "keyword"})
    return hits
