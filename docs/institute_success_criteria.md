# Institute-Specific Success Criteria

This note defines two institute-specific success criteria for the SSL chatbot, aligned to the project PDF's requirement that evaluation should reflect meaningful institute user outcomes rather than only technical behavior.

These criteria are written for the current public-facing SSL scope:

- prospective students, collaborators, journalists, and public users asking about SSL's mission, people, projects, and publications
- users trying to understand SSL's public climate resilience research without reading multiple reports manually

## Success Criterion 1

**Criterion**

A public user can identify the correct SSL page, report, or publication path for their question within one interaction.

**Why this matters**

Many SSL questions are navigational or discovery-oriented. A useful assistant should not only answer, but also direct the user to the right report, people page, projects page, or publications archive quickly.

**Classification metric**

`SC1_pass`

- `Pass`: the answer points the user to the correct source or source family with at least one relevant citation
- `Fail`: the answer cites the wrong source, omits useful source guidance, or sends the user to a non-matching source

**Regression metric**

`SC1_score_1_5`

- `1`: user would still not know where to go next
- `3`: answer is somewhat useful but source direction is incomplete or indirect
- `5`: answer clearly identifies the right SSL page/report/publication path and reduces follow-up effort

**Best-fit question types**

- website factual
- website overview
- publication discovery
- report lookup
- project discovery

## Success Criterion 2

**Criterion**

A public user can get a grounded summary of SSL's public research findings or priorities without reading multiple documents themselves.

**Why this matters**

SSL's public materials are spread across reports, project pages, and publications. A strong assistant should synthesize what matters while staying grounded in the actual corpus and refusing when support is weak.

**Classification metric**

`SC2_pass`

- `Pass`: the answer gives a grounded summary that matches the retrieved evidence and behaves safely when support is weak
- `Fail`: the answer is misleading, overly extractive, unsupported, or fails to refuse when it should

**Regression metric**

`SC2_score_1_5`

- `1`: answer is confusing, unsupported, or not useful to a real user
- `3`: answer is partially grounded but incomplete, noisy, or hard to trust
- `5`: answer is concise, accurate, grounded, and genuinely helpful to a user trying to understand SSL's work

**Best-fit question types**

- topic discovery
- comparison
- synthesis
- ambiguous
- out-of-scope refusal checks

## How To Use These In Evaluation

The scoring template in [phase2_eval_32_scoring_template.csv](../eval/phase2_eval_32_scoring_template.csv) includes:

- one pass/fail field for each criterion
- one 1-5 score for each criterion

Recommended review flow:

1. Check answer correctness, citation presence, retrieval relevance, and correct refusal.
2. Score answer quality, grounding quality, and helpfulness.
3. Score `SC1` and `SC2` only when they meaningfully apply to the question.
4. Record notes about whether the system helped the user complete the institute-relevant task.

## Current partner-review assets

The current institute-facing review packet is split across:

- [phase2_partner_manual_scoring_packet_20.html](./phase2_partner_manual_scoring_packet_20.html) for a print-friendly packet
- [phase2_partner_manual_scoring_packet_20_interactive.html](./phase2_partner_manual_scoring_packet_20_interactive.html) for browser-based review
- [phase2_partner_manual_scoring_20.csv](../eval/phase2_partner_manual_scoring_20.csv) for structured score collection

These files use a 20-question subset from the 32-question Phase 2 candidate set and ask reviewers to score at least 15 questions.

## Current Status

These are proposed institute-specific success criteria prepared for the April 13 checkpoint.

They should be reviewed with the institute partner before the final submission so the wording reflects actual stakeholder priorities as closely as possible.
