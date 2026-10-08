# SSL Faculty Mentor Meeting Summary

## Purpose

This summary captures the main takeaways from the first meeting with the SSL faculty mentor, based on the transcript files in [Transcripts](../Transcripts). The transcript appears to contain three speakers: two students and one faculty mentor.

## Speaker Mapping

- `Speaker 2`: most likely the faculty mentor
- `Speaker 1`: student leading the technical explanation and demo
- `Speaker 3`: second student participating occasionally

This mapping is an inference from the transcript flow and should be treated as best effort.

## Main Scope Clarification

The most important outcome of the meeting was a clarification of project scope. Two different systems were discussed:

1. A public-facing SSL chatbot for external users
2. A broader internal knowledge assistant for SSL staff research and analysis

The faculty mentor made it clear that these are not the same problem.

### External-facing chatbot

The external chatbot would:

- answer questions from public users
- rely on public SSL materials already posted online
- help visitors understand SSL's work
- be easier to evaluate for grounding and hallucination
- be safer from a privacy and data-sovereignty standpoint

The mentor gave examples of the kinds of questions this system might answer:

- What has SSL done?
- What examples of vulnerable groups appear in SSL materials?
- What does SSL say about climate resilience in Greater Boston?

### Internal knowledge assistant

The internal assistant would be much broader. The mentor described it as a tool that could pull from multiple sources, synthesize risk information, and potentially support live research or planning tasks. That version raised major concerns:

- privacy and exposure of research information
- data sovereignty
- whether external AI providers would see the queries or source material
- energy and computing implications
- timeline risk for a short course project

The mentor described this second option as a much larger and riskier project.

## Agreed Direction

The meeting strongly suggests that Phase 1 should focus on the public-facing SSL chatbot.

Reasons:

- it better fits the course timeline
- it aligns with the rubric for a baseline system
- it uses bounded public data
- it is easier to test for correctness and citation quality
- it avoids many of the unresolved privacy concerns

The internal assistant can be treated as a later proof of concept if time remains after the baseline system is working.

## Mentor's Clarification About SSL

The mentor corrected an early misunderstanding about SSL's work. SSL is not mainly collecting climate science data. Instead, SSL focuses on climate justice and the impacts of climate change on historically excluded or vulnerable groups, along with what should be done in response.

This matters for retrieval and demo questions. The system should be optimized for questions about:

- climate justice
- vulnerable populations
- Boston-area communities
- adaptation and resilience
- governance, planning, and funding
- community perspectives and public opinion

## Technical Concerns Raised

The faculty mentor emphasized several technical and ethical concerns:

- The system should preferably run locally or on UMass-controlled infrastructure.
- Public-facing use of public materials is acceptable and lower risk.
- Internal or research-facing use would require much tighter privacy controls.
- If cloud-hosted models are used, the team should be prepared to explain the privacy tradeoffs.
- Energy use and computing cost are also concerns, especially for a climate-focused institute.

The mentor responded positively to precise evaluation metrics and seemed to value measurable system quality.

## Requested Near-Term Outputs

The meeting produced several concrete next steps:

- start with the external-facing chatbot
- use public SSL materials first
- brainstorm realistic user questions
- send the mentor a smaller starter set of questions instead of a huge list
- include edge cases and question diversity
- prepare a short presentation update for Monday, March 30, 2026
- email progress updates over the weekend if possible

The mentor specifically suggested generating benchmark questions from SSL documents and asked for a manageable starter batch. The transcript indicates that sending 10 varied questions would be a good first step.

## Implications For Phase 1

This meeting aligns well with the Phase 1 rubric:

- `working ingestion pipeline`: ingest public SSL documents cleanly
- `baseline retrieval system`: retrieve relevant passages from SSL materials
- `chatbot answering 10 demo questions with citations`: directly matches the mentor's expectations
- `institute meeting summary`: this document supports that requirement
- `brief failure analysis`: can include ambiguity, missing website content, and duplicate-source issues

## Practical Project Decision

For Phase 1, the safest and most defensible interpretation of the meeting is:

Build a public-facing SSL knowledge chatbot over public SSL materials, with visible citations, strong retrieval, and a demo set of 10 grounded questions.

That direction satisfies the course rubric, respects the mentor's concerns, and keeps the system within a realistic weekend implementation scope.

