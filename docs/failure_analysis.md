# Phase 1 Failure Analysis

This note documents the main failure modes we observed while building the baseline SSL chatbot.

## Failure Case 1: Duplicate Source Files

**What failed**

- The source folder contained at least one duplicate PDF.

**Why it matters**

- Duplicate files can cause repeated chunks, duplicated citations, and biased retrieval scores.

**Current mitigation**

- The manifest marks duplicates and the ingestion script skips them.

**Future improvement**

- Extend deduplication from exact file hashes to near-duplicate content detection.

## Failure Case 2: Mixed PDF Encodings

**What failed**

- Several PDFs used different font and text-encoding patterns, which initially caused large portions of reports to extract poorly or appear blank.

**Why it matters**

- If extraction fails, retrieval quality collapses even when the right report is present.

**Current mitigation**

- The PowerShell extractor now handles inherited page resources and a broader range of font aliases.

**Future improvement**

- Add a stronger fallback extractor or OCR path for especially difficult PDFs.

## Failure Case 3: Boilerplate Ranking Too Highly

**What failed**

- Title pages, acknowledgments, contents pages, and front matter often ranked above answer-bearing passages.

**Why it matters**

- The system can retrieve the correct report but still answer badly by quoting the wrong part of it.

**Current mitigation**

- Retrieval now applies boilerplate penalties and source-aware boosts.

**Future improvement**

- Add section-aware chunking and a stronger reranker.

## Failure Case 4: Summary vs. Full Report Ambiguity

**What failed**

- The corpus contains both executive summaries and full reports for some topics.

**Why it matters**

- Short summaries can outrank fuller reports, even when the question needs more precise detail.

**Current mitigation**

- The system keeps document-type metadata and uses heuristic source boosts for some questions.

**Future improvement**

- Add a document-selection layer that prefers full reports for detailed questions and summaries for overview questions.

## Failure Case 5: Broad Synthesis Questions

**What failed**

- Questions like "What has SSL done about climate resilience in Boston?" require multi-document synthesis.

**Why it matters**

- Baseline lexical retrieval is strongest on direct factual lookup and weaker on broad summarization.

**Current mitigation**

- The answer layer now uses lightweight question-pattern handling for the demo set.

**Future improvement**

- Add a stronger synthesis step with explicit multi-source aggregation and citation diversity checks.

## Failure Case 6: Website Coverage Is Still Limited

**What failed**

- The website corpus now includes several high-value public SSL pages, but it is still a curated subset rather than a full crawl of the public SSL site.

**Why it matters**

- Some public-facing questions are better answered from additional SSL web pages, staff pages, project pages, or future event pages that are not yet in the corpus.

**Current mitigation**

- The corpus now includes curated snapshots of the homepage, people page, research page, projects page, and ScholarWorks collection page.

**Future improvement**

- Add reproducible live-refresh ingestion for more SSL web pages.

## Failure Case 7: Figures Are Underused

**What failed**

- Some important findings appear in figures, charts, or tables that are only partially represented in extracted text.

**Why it matters**

- A text-first pipeline can miss evidence that is visually obvious to a human reader.

**Current mitigation**

- Figure-heavy reports are still searchable through surrounding text, captions, and nearby prose when extraction succeeds.

**Future improvement**

- Build a small figure inventory with captions, page references, and plain-language summaries.

## Failure Case 8: Unsupported Questions

**What failed**

- Public users may ask for information that is not present in the current corpus.

**Why it matters**

- A chatbot that guesses missing facts is less trustworthy than one that refuses carefully.

**Current mitigation**

- The demo set includes an unsupported phone-number question, and the system now refuses it instead of inventing an answer.

**Future improvement**

- Add stronger refusal scoring and evaluation for unsupported queries.
