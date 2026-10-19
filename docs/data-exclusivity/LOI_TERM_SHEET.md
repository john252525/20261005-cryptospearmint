# LOI Term Sheet — Exclusive Data License

Status: DRAFT, activation-ready. Not legal advice. Requires qualified counsel review
before execution (see LEGAL_EXECUTION_CHECKLIST.md).
Prepared for: data-exclusivity direction, Option A (see RECOMMENDATION.md)
Inherits from: docs/structural-edge/DATA_EXCLUSIVITY_SCOPE.md

---

## Section 1 — Parties and Scope

This Letter of Intent (LOI) is between [Our Company] (Licensee), an investment
manager, and [Vendor] (Licensor), a data provider, regarding an exclusive license of
[Data Type] for [Duration, e.g. 24 months] across US and EU territories for
[Use Case, e.g. equity signal generation].

Non-binding except Sections 3 (Confidentiality) and 4 (Governing Law), which are
binding upon signature. Binding license agreement to follow within 90 days.

---

## Section 2 — Nine Core Clauses

### Clause 1 — Exclusivity

Purpose: prevent the vendor from selling the same data slice to competing funds,
which is the entire economic basis of this direction. Without meaningful exclusivity
there is no structural edge, only a cost.

Draft language: Licensor warrants that during the License Term no more than [N = 2]
other financial-services licensees receive the same [Data Product] slice for the same
[Use Case/Geography]. Exclusivity defined at the level of the underlying identifiers
(look-through), not merely the packaged product name.

Negotiation priority: MUST-HAVE.

### Clause 2 — Most-Favoured Nation (MFN)

Purpose: price and term protection against the vendor later selling a broader or
cheaper package, which would silently dilute our exclusivity economics.

Draft language: If Licensor grants any third party comparable rights at more
favourable pricing or terms during the License Term, Licensee pricing shall be
retroactively adjusted to match from the date such terms took effect.

Negotiation priority: NICE-TO-HAVE.

### Clause 3 — Redistribution Rights Matrix

Purpose: the derived-signal business model requires internal reuse across affiliated
vehicles; the absence of explicit derived-data rights is the single most common reason
a data contract is unusable for a fund.

Draft language: (i) Internal use only for research and trading; (ii) Derived Signals
may be shared with up to [N = 5] affiliated investment vehicles under common control;
(iii) Raw Data redistribution is strictly prohibited; (iv) Derived Data redistribution
permitted only as described in (ii). "Derived Data" per EU DSM Directive 2019/790
Art. 4 is incorporated by reference.

Negotiation priority: MUST-HAVE.

### Clause 4 — Source-of-Origin Warranty

Purpose: post-App Annie (FTC 2021) the buyer carries regulatory and reputational risk
for unlawful vendor sourcing. A warranty plus indemnity shifts that risk contractually.

Draft language: Licensor warrants that all Data (i) is obtained in compliance with all
applicable privacy laws and platform Terms of Service, (ii) contains no Personal Data
requiring consent beyond consents already obtained by Licensor, and (iii) has an
identifiable lawful basis in both EU and US jurisdictions. Licensor shall indemnify
Licensee against third-party claims arising from breach of this warranty.

Negotiation priority: MUST-HAVE.

### Clause 5 — Compliance Audit Right

Purpose: verify the Clause 4 warranty is not merely contractual boilerplate.

Draft language: Upon 30 days written notice, Licensee may audit Licensor's data
acquisition processes, including source contracts, consent records, and privacy impact
assessments, not more than once per calendar year. Audit costs borne by Licensee
unless material non-compliance is found.

Negotiation priority: NICE-TO-HAVE.

### Clause 6 — Termination Triggers

Purpose: exit path if the vendor's legal position degrades or delivery fails.

Draft language: Either party may terminate for material breach uncured after 30 days
written notice. Licensee may terminate immediately without penalty if Licensor becomes
subject to regulatory enforcement action affecting the lawfulness of the Data, or
becomes insolvent.

Negotiation priority: NICE-TO-HAVE.

### Clause 7 — Derived Data Ownership

Purpose: our models, signals and analytics must remain our property. A vendor claim on
derived analytics would capture the value we create and is a deal-breaker.

Draft language: All Derived Data, analytics, models, features and signals created by
Licensee from the Data are Licensee's sole and exclusive property. Licensor retains no
right, title or interest in Derived Data and may not use it for any purpose.

Negotiation priority: MUST-HAVE.

### Clause 8 — Data Residency

Purpose: Schrems II compliance and the practical reality that EU card/AIS data has
different lawful bases than US data.

Draft language: Data shall be hosted in [Country, e.g. US or EU member state].
Cross-border transfers require 30 days prior written notice and must comply with
Schrems II (CJEU C-311/18) transfer-impact-assessment requirements. No transfer to a
jurisdiction lacking an adequacy decision without Licensee consent.

Negotiation priority: NICE-TO-HAVE.

### Clause 9 — Anti-Assignment / Change of Control

Purpose: a vendor acquisition (e.g. Second Measure to Bloomberg, 2020) can terminate
practical access to the data mid-term and hand our exclusivity to a competitor.

Draft language: Change of control of Licensor requires Licensee consent, not
unreasonably withheld. If control changes, Licensee may terminate without penalty
within 30 days of notice, and any surviving acquirer must honour existing exclusivity
terms for the remainder of the Term.

Negotiation priority: WALK-AWAY if refused. This clause protects the entire
investment; refusing it signals the exclusivity is not real.

---

## Section 3 — Signature Requirements

Authorised officer of Licensee (fund principal or delegated COO) signs; Licensor
signs through CEO or CFO. If the LOI is to be enforceable in a civil-law jurisdiction
(EU counterparty), notarisation or witness attestation may be required — confirm with
counsel per jurisdiction. Two originals, one per party. Electronic signature
acceptable where eIDAS-compliant.

---

## Section 4 — Negotiation Strategy

Fight for three, concede three for speed:

Priority MUST-HAVE (do not sign without): Clause 1 Exclusivity, Clause 4
Source-of-Origin Warranty, Clause 7 Derived Data Ownership. These three define whether
the deal has any value at all.

Concede for speed if vendor pushes back: Clause 5 Audit Right (accept annual-only,
buyer-pays), Clause 8 Data Residency (accept vendor's default jurisdiction if EU data
not central to the use case), Clause 2 MFN (accept as "reasonable efforts" rather than
retroactive adjustment).

Walk-away triggers, in order of severity:

1. Clause 9 Anti-Assignment refused outright — vendor intends to be acquired and
   does not want constraints; the exclusivity is not durable.
2. Clause 7 Derived Data Ownership contested — vendor claims rights in our models;
   this is a fundamental conflict of interest.
3. Clause 1 exclusivity reduced to "marketing exclusivity" (i.e. they will not
   market to competitors but will still sell to them) — that is not exclusivity.
4. Clause 4 warranty refused — vendor knows its sourcing is not clean.

Escalation: if any walk-away trigger is hit, terminate the conversation politely and
move to the next HIGH-priority vendor on VENDOR_SHORTLIST.md. There are 20 candidates;
no single vendor is essential.
