# Project Outline Reference

This is a working reference distilled from [CS 438 638 Term Project (3).pdf](../CS%20438%20638%20Term%20Project%20(3).pdf) (add the course PDF at the repository root if the link is broken). We should keep checking our implementation and docs against this outline.

The dates and rubric items below are preserved from the course PDF as the source of truth. Phase 1 now serves as our baseline checkpoint, but the rubric remains the standard we should keep using as coverage expands.

## Core System Requirements

The project expects a real-world RAG chatbot that can:

- collect institute materials such as webpages, PDFs, reports, staff pages, and other relevant documents
- extract clean text and structured metadata such as title, source type, URL, and publication date when available
- segment documents into searchable passages using appropriate chunking strategies
- construct a retrieval index using keyword search, vector search, or hybrid retrieval
- answer questions with citations grounded in retrieved evidence
- refuse or limit answers when the corpus does not support a claim

## Institute-Partner Expectations

Teams should learn from the institute partner:

- what questions users frequently ask
- what information is most important to surface
- which documents may not be publicly available on the website

The pipeline should be:

- reproducible
- maintainable
- refreshable when new documents are added

## Phase 1

**Due:** March 30, 2026 at 12:00 PM

**Weight:** 20%

**Required submission items**

- working ingestion pipeline
- baseline retrieval system
- chatbot answering 10 demo questions with citations
- institute meeting summary
- brief failure analysis

**Phase 1 grading rubric**

- Working ingestion pipeline: 20
- Baseline retrieval quality: 20
- Chatbot answers with citations: 20
- Institute meeting and communication summary: 10
- Demo dataset quality: 10
- Failure analysis: 10
- Reproducibility (README): 10

## Later Milestones

- Phase 2 due April 13, 2026
- Final submission due May 11, 2026

The PDF notes that later-phase details will be announced separately.

## What We Should Keep Checking

Every major change should be checked against these questions:

- Does this improve the ingestion pipeline?
- Does this improve retrieval quality?
- Does this improve answer grounding or citation quality?
- Does this help reproducibility?
- Does this help the 10-question demo set or failure analysis?
- Does this stay within the public-facing SSL scope discussed with Dr. Balachandran?

## Current Phase 1 Interpretation

For our project, the safest Phase 1 interpretation is:

- build a public-facing SSL chatbot over public SSL materials
- keep the system text-first and citation-first
- prioritize reliability, grounded answers, and refusal behavior over ambitious extra features
- make the repo easy to rerun and easy to explain

## Practical Build Priorities

When deciding what to work on next, the Phase 1 priority order should be:

1. ingestion reliability
2. retrieval quality
3. citation quality
4. demo question coverage
5. failure analysis and README
6. optional extras such as figures or broader web ingestion

