# 50-Question Coverage Expansion Plan

This file expands the current benchmark into a broader 50-question set while keeping the original Phase 1 deliverable stable.

Primary dataset:

- [question_coverage_50.json](question_coverage_50.json)

Why this structure makes sense:

- It keeps the official 10 Phase 1 questions as anchor questions.
- It adds broader website, report, program, policy, place-based, comparison, synthesis, multilingual, and refusal coverage.
- It stays inside the public-facing SSL scope described in [project_outline_reference.md](../docs/project_outline_reference.md).
- It is designed to expose current system limits instead of only rewarding benchmark-specific tuning.

## Current Status

The broader benchmark is now wired into the same evaluation runner as the official 10-question set.

Latest aggregate totals for this set are summarized in [phase1_metrics.md](phase1_metrics.md) (50-question coverage section).

Current results:

- [question_coverage_50_results.md](question_coverage_50_results.md)

## Rollout Breakdown

- Baseline anchor questions carried forward: `10`
- New website and public-facing questions: `7`
- New community, place-based, and multilingual report questions: `10`
- New policy, governance, financing, program, and infrastructure questions: `14`
- New transient-population, regional-planning, and migration questions: `7`
- New synthesis question: `1`
- New out-of-scope refusal question: `1`

## Suggested Rollout Order

1. Run the existing official 10 as the stability baseline.
2. Add the next `10-15` direct factual questions first.
3. Add comparison and synthesis questions after direct factual retrieval is stable.
4. Add the multilingual question as a separate check so language-specific failures are visible.
5. Keep the out-of-scope question in the set so refusal behavior remains part of evaluation.

## Best Use For The Next Iteration

Use this 50-question set to answer three practical questions:

1. Which questions are already supported with good citations?
2. Which questions fail because retrieval is weak?
3. Which questions fail because answer generation is over-tuned to the original benchmark?

## What To Avoid

- Do not rewrite the pipeline just to satisfy one or two new questions.
- Do not keep adding hard-coded question rules for every new prompt.
- Do not mix official submission questions and experimental coverage questions without labeling them clearly.

## Recommended Next Implementation Step

The question-file path workflow is now implemented in [Run-Demo.ps1](../src/Run-Demo.ps1), so we can run:

- the official 10-question set
- the broader 50-question expansion set

without changing the code each time.

The next useful step is not adding more questions immediately. It is:

1. manually reviewing answers that are technically supported but still not polished enough for end users
2. deciding which remaining weaknesses are retrieval problems versus answer-formatting problems
3. adding regression checks so sparse-PDF fallback indexing stays stable
4. using that review to guide the first user interface layer

