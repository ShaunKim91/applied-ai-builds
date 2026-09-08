"""A fully FICTIONAL corpus of insurance regulations, precedent rulings, DOI
bulletins, and catastrophe-event reports across six invented jurisdictions.

**Why fictional, not real web search, for claims/regulatory research**:
grounding a fictional company's (Fenwick Mutual) claims decisions in real
scraped web content about real states' real insurance law would be
logically incoherent (Fenwick Mutual doesn't operate in any real
jurisdiction) AND would risk the LLM echoing real regulatory text as if
Verity had verified it — a real hallucination-adjacent risk this project's
standing "no hallucination" rule requires avoiding. So Verity's claims
research (Research page, Precedent Brief mode) is grounded ONLY in this
curated, deterministic, clearly-fictional corpus — never live web search.
(The separate Vendor Adoption Radar feature DOES use real live web search,
since evaluating a real AI/InsurTech vendor tool is genuinely
real-world research — see search/web_search.py's `radar_search()`.)

Every jurisdiction name, statute citation, case name, and bulletin number
below is invented for this demo. None of it should be treated as, or cited
as if it were, real law.
"""

JURISDICTIONS = ["Ashford", "Belmont Bay", "Cedermoor", "Dunraven", "Elmsworth", "Fairhaven"]

# Each entry mirrors a real search result's shape (title/href/body) so the
# existing rerank pipeline can treat this corpus identically to a live
# search response.
_DOCS = [
    # --- Ashford ---
    {
        "title": "Ashford Insurance Code § 2210.4 — Prompt Payment of Claims",
        "href": "https://statutes.fenwick-demo.example/ashford/ins-2210-4",
        "body": "An insurer doing business in Ashford must accept or deny a first-party property claim within 30 days of receiving a complete proof of loss. A denial must be in writing and state every ground relied upon; grounds not stated within the 30-day window may not later be raised as a basis for denial.",
    },
    {
        "title": "Farrow v. Meridian Casualty, Ashford Ct. App. 2019",
        "href": "https://cases.fenwick-demo.example/ashford/farrow-v-meridian-2019",
        "body": "The Ashford Court of Appeals held that an insurer's failure to state a specific coverage exclusion in its initial denial letter waives that exclusion as a later litigation defense, reaffirming the 'raise it or lose it' rule under Ins. Code § 2210.4.",
    },
    {
        "title": "Ashford DOI Bulletin No. 2024-07 — Bad-Faith Claims Handling",
        "href": "https://doi.fenwick-demo.example/ashford/bulletin-2024-07",
        "body": "The Ashford Department of Insurance reminds carriers that a pattern of unreasonably delayed payouts, even absent a single flagrant denial, can independently support a bad-faith finding under the state's unfair claims practices framework.",
    },
    # --- Belmont Bay ---
    {
        "title": "Belmont Bay Rev. Stat. § 44.812 — Statute of Limitations, Property Claims",
        "href": "https://statutes.fenwick-demo.example/belmont-bay/rs-44-812",
        "body": "A first-party property insurance claim in Belmont Bay must be filed within 2 years of the date of loss. Reinsurance and subrogation claims arising from the same loss follow a separate 3-year period under § 44.815.",
    },
    {
        "title": "Okafor v. Harborline Mutual, Belmont Bay Sup. Ct. 2021",
        "href": "https://cases.fenwick-demo.example/belmont-bay/okafor-v-harborline-2021",
        "body": "The Belmont Bay Supreme Court clarified that the 2-year filing clock under § 44.812 is tolled during any period the insurer is actively investigating the claim in good faith, but resumes running once a denial letter is issued.",
    },
    {
        "title": "Belmont Bay DOI Bulletin No. 2023-11 — Catastrophe Claim Surge Handling",
        "href": "https://doi.fenwick-demo.example/belmont-bay/bulletin-2023-11",
        "body": "Following a declared catastrophe event, Belmont Bay permits insurers a 45-day (rather than the standard 30-day) claim-response window, provided the extension is publicly disclosed within 5 business days of the declaration.",
    },
    # --- Cedermoor ---
    {
        "title": "Cedermoor Ins. Code § 3814.12 — Prompt Payment of Claims",
        "href": "https://statutes.fenwick-demo.example/cedermoor/ins-3814-12",
        "body": "Cedermoor requires payment of an undisputed portion of a first-party claim within 15 days of acknowledgment of coverage, even while a disputed portion remains under investigation — partial withholding of the undisputed amount is itself an unfair claims practice.",
    },
    {
        "title": "Delacroix v. Union Assurance Co., Cedermoor Ct. App. 2020",
        "href": "https://cases.fenwick-demo.example/cedermoor/delacroix-v-union-2020",
        "body": "The Cedermoor Court of Appeals held that an insurer's internal payout-calculation worksheet is discoverable in a bad-faith action once the insurer places its claims-handling process at issue, rejecting a work-product objection over routine estimate documents.",
    },
    {
        "title": "Cedermoor DOI Bulletin No. 2022-03 — Contractor Estimate Red Flags",
        "href": "https://doi.fenwick-demo.example/cedermoor/bulletin-2022-03",
        "body": "The Cedermoor DOI advises adjusters to flag repair estimates exceeding 40% above the regional cost index for further review before payout, particularly where the same contractor appears across multiple unrelated claims within a short window.",
    },
    # --- Dunraven ---
    {
        "title": "Dunraven Code Ann. § 19-220 — Post-Binding Loss Reporting",
        "href": "https://statutes.fenwick-demo.example/dunraven/ca-19-220",
        "body": "A claim reported within the first 10 days of a policy's effective date is not automatically presumed fraudulent under Dunraven law, but the insurer may request additional documentation of the loss circumstances without triggering a bad-faith delay finding, provided the request is made within 5 business days.",
    },
    {
        "title": "Whitmore v. Cascade Indemnity, Dunraven Sup. Ct. 2018",
        "href": "https://cases.fenwick-demo.example/dunraven/whitmore-v-cascade-2018",
        "body": "The Dunraven Supreme Court held that a documented pattern of prior claims naming the same unidentified 'phantom vehicle' across a claimant's history is admissible circumstantial evidence in a fraud-based denial, without requiring a criminal conviction as a precondition.",
    },
    # --- Elmsworth ---
    {
        "title": "Elmsworth Ins. Reg. 12 VAC 90-40 — Reinsurance Recovery Currency Conversion",
        "href": "https://statutes.fenwick-demo.example/elmsworth/reg-12vac90-40",
        "body": "Where a reinsurance recovery is denominated in a foreign currency, Elmsworth requires the ceding insurer to disclose the exact conversion rate and date used in its claim file, and to use a rate no more than 3 business days stale at time of settlement.",
    },
    {
        "title": "Elmsworth DOI Bulletin No. 2021-09 — Duplicate Claim Detection",
        "href": "https://doi.fenwick-demo.example/elmsworth/bulletin-2021-09",
        "body": "The Elmsworth DOI encourages carriers to cross-reference loss address and vehicle identification across claimant names, noting that duplicate-claim rings frequently file under different household members within the same reporting window.",
    },
    # --- Fairhaven ---
    {
        "title": "Fairhaven Rev. Code § 61.335 — Coastal Wind & Hail Deductible Disclosure",
        "href": "https://statutes.fenwick-demo.example/fairhaven/rc-61-335",
        "body": "Insurers writing coastal property in Fairhaven must disclose any separate, higher wind/hail deductible in a distinct, boldfaced section of the declarations page — a deductible not so disclosed is unenforceable and the standard deductible applies instead.",
    },
    {
        "title": "Bishara v. Fairhaven Coastal Mutual, Fairhaven Ct. App. 2022",
        "href": "https://cases.fenwick-demo.example/fairhaven/bishara-v-coastal-2022",
        "body": "The Fairhaven Court of Appeals invalidated a wind/hail deductible that was disclosed only in a policy endorsement rider rather than on the declarations page itself, applying the standard deductible under Rev. Code § 61.335.",
    },
    # --- Cross-jurisdiction catastrophe/weather event reports ---
    {
        "title": "Regional Hail Event Report — Coastal Belmont Bay & Fairhaven, March 2025",
        "href": "https://catreports.fenwick-demo.example/2025-03-coastal-hail",
        "body": "A severe hail line tracked across coastal Belmont Bay and northern Fairhaven on March 14-15, 2025, producing golf-ball-sized hail and an estimated regional claim surge of 3,200 property claims within 72 hours, triggering Belmont Bay's DOI Bulletin 2023-11 extended response window.",
    },
    {
        "title": "Wildfire Event Report — Dunraven Foothills, September 2024",
        "href": "https://catreports.fenwick-demo.example/2024-09-dunraven-wildfire",
        "body": "A wind-driven wildfire in the Dunraven foothills damaged an estimated 640 structures across 3 counties between September 2-6, 2024; state-declared catastrophe status extended standard filing deadlines by 60 days under emergency order.",
    },
]


def all_documents() -> list[dict]:
    return list(_DOCS)


def search(query: str, jurisdiction: str | None = None, top_k: int = 8) -> list[dict]:
    """Deterministic keyword-overlap filter over the fictional corpus —
    intentionally simple (no live network call, no external service): this
    corpus is small and fixed by design, so a lightweight keyword match
    plus the existing embedding rerank pipeline downstream is sufficient
    and keeps the whole path fully offline and reproducible."""
    q_terms = {t.lower() for t in query.split() if len(t) > 2}
    pool = _DOCS if not jurisdiction else [d for d in _DOCS if jurisdiction.lower() in d["href"].lower() or jurisdiction.lower() in d["title"].lower()]
    scored = []
    for doc in pool:
        haystack = f"{doc['title']} {doc['body']}".lower()
        overlap = sum(1 for t in q_terms if t in haystack)
        if overlap > 0 or not q_terms:
            scored.append((overlap, doc))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    results = [doc for _, doc in scored[:top_k]]
    # Fall back to the whole jurisdiction pool (or whole corpus) if nothing
    # matched by keyword — the downstream embedding rerank still does real
    # work, and an honest "insufficient evidence" is a valid, real outcome
    # the UI surfaces rather than silently returning nothing.
    return results if results else pool[:top_k]
