# Full QA Review: 50-Question Coverage Set

> Note: This review captures the pre-cleanup baseline from April 5, 2026. The answer layer was revised afterward, so use it as a diagnostic snapshot rather than the latest quality verdict.

Reviewed on: `2026-04-05`
Source benchmark: [question_coverage_50_results.md](question_coverage_50_results.md)
Question set: [question_coverage_50.json](question_coverage_50.json)

## Review criteria
- `Strong`: accurate, grounded, useful, and presentation-ready
- `Polish`: grounded enough to keep, but needs cleaner wording or tighter source use
- `Fix`: answer is raw, incomplete, drifted off question, or not trustworthy enough to present as-is

## Summary
- `Strong`: `18/50`
- `Polish`: `6/50`
- `Fix`: `26/50`

The benchmark is currently very good at:
- retrieving preferred sources
- attaching citations
- refusing unsupported budget questions

The benchmark is currently weakest at:
- turning noisy PDF passages into clean natural-language answers
- keeping synthesis/comparison questions focused on the actual ask
- preventing contamination from nearby but irrelevant report text

## Highest-priority fixes
- `xq17`: does not actually compare the homepage and ScholarWorks page
- `xq21`: not a usable summary of `Views that Matter`
- `xq25`: East Boston recommendations answer is polluted by unrelated MVP timeline text
- `xq31` and `xq32`: governance sub-questions are swamped by OCR/extractive debris
- `xq36` and `xq37`: harbor-barrier answers are mixed with unrelated finance/MVP text
- `xq41`: contaminated with transient-population content
- `xq42`: directly answers the wrong question
- `xq45`: does not clearly answer `Boston and Cape Cod`
- `xq48`: migration-paper answer uses the wrong sources and wrong content
- `xq49`: fails to compare financing and governance as complementary reports

## Full pass
| ID | Status | QA note |
| --- | --- | --- |
| `xq01` | `Strong` | Clear overview answer with appropriate public web citations. |
| `xq02` | `Strong` | Good synthesis of community concerns; concise and grounded. |
| `xq03` | `Strong` | Precise factual answer with the right cited report page. |
| `xq04` | `Strong` | Funding mechanisms are named correctly without obvious invention. |
| `xq05` | `Strong` | Governance recommendations are summarized clearly enough for presentation. |
| `xq06` | `Strong` | Good comparison of survey vs focus-group evidence. |
| `xq07` | `Strong` | Strong East Boston answer with clear framing around gentrification and displacement. |
| `xq08` | `Strong` | Useful MVP overview with proper emphasis on purpose, collaboration, and equity. |
| `xq09` | `Strong` | Broad synthesis, but still readable and citation-supported. |
| `xq10` | `Strong` | Direct website-based factual answer. |
| `xq11` | `Polish` | Starts correctly, but drifts into pasted snapshot text instead of a tight public-framing summary. |
| `xq12` | `Fix` | Mixes homepage framing with stakeholder-report language and overstates who SSL explicitly centers. |
| `xq13` | `Fix` | Includes irrelevant director/offline snapshot detail instead of a clean summary of collection contents. |
| `xq14` | `Strong` | Clean named-project list from the projects page. |
| `xq15` | `Strong` | Direct website phone-number answer with public citation. |
| `xq16` | `Polish` | Right content, but too extractive and list-like for a user-facing answer. |
| `xq17` | `Fix` | Does not actually compare homepage emphasis vs ScholarWorks emphasis. |
| `xq18` | `Strong` | Clear answer about health and air-quality burdens from the right report. |
| `xq19` | `Fix` | Mostly pasted report fragments; does not cleanly summarize preparedness concerns. |
| `xq20` | `Strong` | Good explanation of what `Voices` adds beyond `Views`. |
| `xq21` | `Fix` | Raw table/page fragments; not a usable answer to the survey-opinions question. |
| `xq22` | `Polish` | Substantively plausible, but generic and too close to the `xq02` answer. |
| `xq23` | `Strong` | Clear and useful answer about institutional listening and community knowledge. |
| `xq24` | `Strong` | Solid explanation of how community knowledge connects to equitable action. |
| `xq25` | `Fix` | East Boston recommendations answer is polluted by unrelated timeline and report-history text. |
| `xq26` | `Fix` | Topic is correct, but answer is bloated and drifts into recommendations instead of the relationship between the two reports. |
| `xq27` | `Polish` | Spanish retrieval works, but the question text has encoding issues and the answer is too extractive and long. |
| `xq28` | `Fix` | Uses the right sources, but the answer is still stitched from raw report text instead of a clean three-scale summary. |
| `xq29` | `Polish` | Topic is right, but the answer is too long and extractive for a simple role-of-insurance question. |
| `xq30` | `Fix` | One recommendation is visible, but the answer collapses into citation debris and irrelevant finance references. |
| `xq31` | `Fix` | The Infrastructure Coordination Committee answer is present, but buried in OCR noise and duplicated text. |
| `xq32` | `Fix` | The Climate Research Advisory Organization answer is partly there, but swamped by unrelated governance text. |
| `xq33` | `Fix` | Returns a generic governance summary rather than explaining how governance scale relates to flooding responses. |
| `xq34` | `Fix` | Does not clearly compare executive-summary emphasis against the full report. |
| `xq35` | `Fix` | Answers with a conclusion favoring shore-based adaptation rather than describing what the report analyzes. |
| `xq36` | `Fix` | Mixes harbor-barrier tradeoffs with unrelated financing text, which makes the answer hard to trust. |
| `xq37` | `Fix` | Contains corrupted title/citation text and an unrelated MVP citation. |
| `xq38` | `Strong` | Good restatement of the MVP program purpose. |
| `xq39` | `Fix` | Seven lessons are not summarized cleanly; answer is mostly pasted conclusion text. |
| `xq40` | `Fix` | Core equity point is present, but the answer is unreadable and repetitive. |
| `xq41` | `Fix` | Cross-sector collaboration answer is contaminated with transient-population content and should not be trusted as-is. |
| `xq42` | `Fix` | Directly answers the wrong question by repeating the two transient populations instead of explaining why they are overlooked. |
| `xq43` | `Fix` | Relevant evidence is present, but the answer is pasted and cluttered rather than summarized. |
| `xq44` | `Fix` | Mostly explains who H-2B workers are rather than the climate-impact challenges they face. |
| `xq45` | `Fix` | Does not answer `Boston and Cape Cod` clearly; answer is dominated by noisy extractive text. |
| `xq46` | `Polish` | Grounded in the right report, but too extractive and long for a stakeholder-mapping summary. |
| `xq47` | `Fix` | Too extractive; should summarize relationship types and sector-spanning ties more directly. |
| `xq48` | `Fix` | Uses the wrong sources and wrong content for the migration-paper themes question. |
| `xq49` | `Fix` | Uses governance-only content and fails to explain how financing and governance complement each other. |
| `xq50` | `Strong` | Correct refusal behavior for an unsupported budget question. |

## Recommended cleanup order
1. Website and overview answers:
   - `xq11`, `xq12`, `xq13`, `xq16`, `xq17`
2. Community and East Boston answers:
   - `xq19`, `xq21`, `xq25`, `xq26`, `xq27`
3. Financing, governance, and harbor-barrier answers:
   - `xq28` to `xq37`, `xq49`
4. MVP and transient-population answers:
   - `xq39` to `xq45`
5. Regional planning and migration answers:
   - `xq46`, `xq47`, `xq48`

## Bottom line
The project is in a strong place on citation discipline and refusal behavior, but the expanded 50-question set still has a large answer-quality gap. The next phase should prioritize rewriting and generalizing answer assembly for the `Fix` group before spending more time on UI polish or adding more coverage.

