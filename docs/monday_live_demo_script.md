# Live Demo Runbook

This note is a presenter-facing companion to the current Beacon BOT demo materials. It keeps the meeting focused on the strongest parts of the system: a local, citation-first SSL chatbot over public reports and curated SSL webpages.

## Goal

Run a short live Beacon BOT demo that feels reliable, easy to explain, and easy for Dr. B to explore.

## Before the meeting

- Open [phase1_status_update.html](../slides/phase1_status_update.html) if you want a slide-based walkthrough.
- Open [metrics_visuals.html](../docs/metrics_visuals.html) if you want a one-page metrics visual.
- Keep [phase1_demo_answers.md](../eval/phase1_demo_answers.md) open as the polished answer key.
- Keep [phase1_demo_questions_results.md](../eval/phase1_demo_questions_results.md) open as the current benchmark backup.
- Keep [command_key.txt](./command_key.txt) open for quick commands.
- From the project root, make sure the corpus is already built before the meeting.

## Suggested opening

Use a short framing statement such as:

"Beacon BOT is a local, citation-first chatbot over public Sustainable Solutions Lab materials. We ingest SSL reports and curated SSL webpages, retrieve the most relevant passages, and return grounded answers with visible citations and supporting evidence."

## Fast startup

Use the launcher in [command_key.txt](./command_key.txt). The prototype opens at [http://127.0.0.1:8765](http://127.0.0.1:8765) on both macOS and Windows.

## Recommended live flow

### 1. Start with a clean overview

Ask:

```text
What is the Sustainable Solutions Lab, and what does it focus on?
```

What to point out:

- Beacon BOT answers from public SSL materials.
- The answer is grounded and easy to verify.
- This is the quickest way to frame the scope of the project.

### 2. Show a simple factual lookup

Ask:

```text
Who is the current director of the Sustainable Solutions Lab?
```

What to point out:

- The answer resolves directly to the SSL people page.
- This shows that Beacon BOT handles public website facts cleanly.
- The evidence panel now surfaces the relevant staff snippet cleanly enough to narrate live.

### 3. Show cross-report comparison

Ask:

```text
How are "Voices that Matter" and "Views that Matter" different in the kind of evidence or perspective they provide?
```

What to point out:

- The answer uses two different SSL reports.
- This shows report-level retrieval rather than only website lookup.
- The citations make it easy to explain where each piece of the comparison came from.

### 4. Hand over a strong follow-up topic

Invite Dr. B to try one of these:

- What concerns does the East Boston resilience work raise about climate adaptation, gentrification, and displacement?
- What kinds of funding mechanisms are discussed in SSL's climate resilience financing work?
- What does the SSL report say about the Massachusetts Municipal Vulnerability Preparedness (MVP) Program in the Greater Boston region?

## Current metrics to cite live

- Official 10-question benchmark: `10/10` citation requirement satisfied, `10/10` support expectation matched, `10/10` preferred-source hit in top 5.
- Phase 2 candidate 32-question set: `31/31` citation requirement satisfied, `32/32` support expectation matched, `31/31` preferred-source hit in top 5.
- Broader 50-question set: `49/49` citation requirement satisfied, `50/50` support expectation matched, `50/50` preferred-source hit in top 5.

## If asked about limitations

Use a short, honest answer such as:

"The current system is strongest on direct factual lookup and report-grounded questions. The main open issues are broad synthesis prompts that still need more polish and the fact that figures and tables are not yet treated as first-class evidence objects."

## Closing line

"The baseline is now reliable enough to demonstrate grounded SSL question answering live, and the next step is improving the few remaining extraction and benchmark gaps rather than rebuilding the whole system."
