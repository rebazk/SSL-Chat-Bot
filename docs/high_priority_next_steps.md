# High Priority Next Steps

The root [README](../README.md) links here for the ordered engineering backlog so priority lists stay in one place.

## Done (keep for history)

- [x] Reduce query latency by reusing a cached search index instead of rebuilding it on every query.
- [x] Fix Beacon BOT UI freshness so it notices corpus rebuilds and clears stale cached answers.
- [x] Consolidate the webpage refresh path: `Refresh-Webpages.ps1` delegates to `refresh_webpages.py`.
- [x] Add baseline API smoke tests: `tests/test_serve_ui_api.py` and `tests/Smoke-BeaconOneQuestion.ps1`.
- [x] Fix extraction or indexing quality for `ssl_pdf_003` so the migration-paper questions do not return uncited supported answers.
- [x] Improve text cleanup so mojibake does not leak into user-facing answers and evidence cards.
- [x] Harden Beacon BOT server/worker (body size cap, safe URLs, LRU cache, read timeout, `top` clamp) and UI stale-result handling.

## High priority (ordered)

1. **Wire automated checks** — Run `python -m unittest tests.test_serve_ui_api -v` and `tests/Smoke-BeaconOneQuestion.ps1` in CI or pre-commit so regressions are caught without full 50/53 suites.
2. **Split `SslPipeline.ps1`** — Extract modules (support checks, search/index, special answers, formatting) to lower risk when tuning synthesis and support rules.
3. **Regression breadth** — Extend or add JSON sets for unsupported refusals, citations, and preferred-source ranking beyond `eval/regression_tricky_prompts.json`; re-run 50-q, all-PDF, and tricky after pipeline edits.
4. **Answer polish** — Manual pass on “correct but ugly” answers (e.g. director naming, noisy snippets); align with institute-facing tone in `eval/phase1_demo_answers.md` where it matters.
5. **Teammate workflow** — One clear path: how to start Beacon BOT, refresh corpus, run smoke + one benchmark slice, and where to log issues (short `docs/` note if needed).
6. **Retrieval roadmap** — After lexical + heuristics are stable, plan hybrid / reranking for sparse-query cases (e.g. fellowship-style prompts) instead of more one-off rules.
7. **Figures / tables** — Inventory high-value report visuals; decide whether to index captions or treat figures as first-class evidence (`docs/failure_analysis.md`).

## Phase 1 -> Phase 2 execution checklist

- [ ] Build a 30-50 question SSL evaluation set with expected answer points.
- [x] Add a metrics pipeline with simple visuals (accuracy, support, refusal behavior, latency). Live multiturn stats merge into `eval/metrics_snapshot.json` and render in `docs/metrics_visuals.html`; headline benchmarks unchanged.
- [x] Strengthen in-scope guardrails, including denial for personal/sensitive information and out-of-scope questions.
- [x] Add follow-up question support plus short session memory.
- [ ] Add recommended question UI improvements for guided starts.
- [ ] Produce a one-page evaluation results summary for demos.
