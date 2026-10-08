# Manual Scoring 1 Feedback-to-Fix Plan

Source reviewer: B.R. Balachandran (ED)  
Baseline file: `eval/manualscoring1_dr_b.csv`  
Fix pass started: 2026-05-05
Verification refreshed: 2026-05-11

## Baseline

| Metric | Baseline |
|---|---:|
| Questions reviewed | 20 |
| Average answer quality | 4.15 / 5 |
| Average grounding | 4.10 / 5 |
| Average helpfulness | 4.05 / 5 |
| Overall scoring average | 4.10 / 5 |
| SC1 pass rate | 16 / 20 |
| SC2 pass rate | 17 / 20 |
| Priority fix targets | 5 / 20 |

## Priority Fix Targets

| Question | Issue from Dr. B | Planned fix | Status |
|---|---|---|---|
| p2q05 | Governance answer was useful, but cited page 12; pages 64-65 are better references. | Prefer the full governance report's district-scale governance pages 64-65 for the broad governance/policy recommendation answer. | Fixed and verified in `eval/manualscoring1_postfix_results.md`: answer cites p. 64. |
| p2q07 | East Boston answer cited page 44, which is a references page. | Keep the answer content but pin citations to substantive East Boston pages covering gentrification, displacement, and trust concerns. | Fixed and verified in `eval/manualscoring1_postfix_results.md`: answer cites p. 6 and p. 37. |
| p2q08 | MVP answer did not respond to the question and returned the generic SSL overview. | Narrow the broad SSL mission detector and add a targeted MVP Program answer grounded in the MVP report and SSL research page. | Fixed and verified in `eval/manualscoring1_postfix_results.md`: answer now summarizes the MVP report. |
| p2q09 | Broad Boston climate resilience answer did not respond to the question and returned the generic SSL overview. | Narrow the broad SSL mission detector and return a multi-source synthesis across public research, community studies, policy reports, and East Boston/place-based work. | Fixed and verified in `eval/manualscoring1_postfix_results.md`: answer now gives multi-source synthesis. |
| p2q18 | Health/air-quality answer was too generic; preferred answer provided; page-specific citation not appropriate for a summary statement. | Use Dr. B's preferred answer text and cite the article/report title without a page number. | Fixed and verified in `eval/manualscoring1_postfix_results.md`: answer uses preferred summary and no page number. |

## Post-Fix Evidence To Save

- Rerun the 20-question partner/manual subset and save as `eval/manualscoring1_postfix_results.md`. Done: 20/20 support expectation matched, 19/19 citation requirement met, 19/19 preferred source hit.
- Rerun the Phase 2 32-question candidate set and save as `eval/phase2_eval_32_candidate_postfix_results.md`. Done: 32/32 support expectation matched, 31/31 citation requirement met, 31/31 preferred source hit.
- Save chart-ready before/after metrics as `eval/manualscoring1_before_after_visual_metrics.csv`. Done, with manual post-fix score averages marked as requiring a human rescore.
- Update this log with the actual post-fix answer status after the reruns. Done.
