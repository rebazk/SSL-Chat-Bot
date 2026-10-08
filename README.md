# Beacon BOT

**A citation-grounded research assistant for the Sustainable Solutions Lab at the University of Massachusetts Boston.**

Beacon BOT is a local, browser-based question-answering system designed to help users explore public research and resources from UMass Boston's **Sustainable Solutions Lab (SSL)**. It retrieves relevant passages from SSL publications and webpage snapshots, produces concise answers, and displays citations and supporting evidence so users can check the sources behind a response.

The project combines a reproducible document-retrieval pipeline with an optional large language model (LLM) answer-generation step and an evaluation workflow covering retrieval, citations, answer quality, and human feedback.

## Features

- **Source-grounded answers:** Retrieves evidence from an indexed collection of SSL PDFs and public webpage snapshots.
- **Visible citations:** Shows source references and supporting retrieval results alongside answers.
- **Optional LLM-assisted responses:** Uses OpenRouter to summarize retrieved passages when configured; otherwise retains an extractive-answer fallback.
- **Local web interface:** Browser-based chat interface with source/evidence cards and limited multi-turn follow-up handling.
- **Corpus refresh and rebuilding:** Recreates searchable documents, chunks, and a cached lexical index from a source manifest.
- **Evaluation tools:** Includes benchmark question sets, citation and retrieval checks, ROUGE/BERTScore/QA metrics, LLM-as-judge scripts, and human-review materials.
- **Scope and privacy checks:** Includes handling for off-topic requests and certain patterns of sensitive personal information.

## How it works

```text
SSL PDFs + webpage snapshots
              |
              v
     Source manifest and ingestion
              |
              v
     Text extraction and chunking
              |
              v
       BM25-style lexical search
              |
              v
      Relevant passages + sources
              |
              v
   Extractive answer / optional LLM
              |
              v
      Beacon BOT web interface
        Answer + citations
```

1. **Ingest:** `src/Build-Corpus.ps1` reads `data/processed/sources_manifest.csv`, extracts source text, and creates `documents.jsonl` and `chunks.jsonl`.
2. **Retrieve:** PowerShell pipeline components build and query a cached BM25-style lexical index.
3. **Answer:** The backend uses retrieved evidence to produce an answer. When `OPENROUTER_API_KEY` is configured, `src/llm_answer.py` can generate a concise, evidence-based rewrite; an extractive response remains available as a fallback.
4. **Display:** `src/serve_ui.py` serves the local web interface in `ui/` and returns answers with source evidence.
5. **Evaluate:** Scripts and datasets in `eval/` test citation coverage, retrieval behavior, response quality, and selected failure cases.

## Repository structure

| Location | Contents |
| --- | --- |
| `src/` | Ingestion, retrieval, answer generation, web server, and evaluation scripts |
| `ui/` | Chat interface, JavaScript, CSS, and visual assets |
| `source material/` | SSL PDF documents used by the local corpus |
| `data/raw/` | Saved SSL webpage snapshots and extraction fallbacks |
| `data/processed/` | Source manifest and generated searchable corpus/index files |
| `eval/` | Question sets, benchmark outputs, automated metrics, and review records |
| `docs/` | Project documentation, manual scoring, failure analysis, and visual reports |
| `tests/` | API and smoke-test scripts |

## Getting started

### Requirements

- Python 3
- PowerShell (`powershell` on Windows or `pwsh` on macOS/Linux) for corpus building and retrieval
- Python packages in `requirements.txt` for optional LLM integration and evaluation tools
- `pypdf` for the PDF-extraction fallback
- An **optional** OpenRouter API key for LLM-assisted answers and live LLM evaluation

Run commands from the repository root.

### 1. Install Python dependencies

**Windows (PowerShell):**

```powershell
py -m pip install -r requirements.txt
py -m pip install pypdf
```

**macOS/Linux:**

```bash
python3 -m pip install -r requirements.txt pypdf
```

### 2. Build the local corpus

The repository contains the source manifest, PDF documents, and saved webpage snapshots. The searchable `documents.jsonl`, `chunks.jsonl`, and index cache are generated locally and are not committed.

**Windows:**

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\src\Build-Corpus.ps1
```

**macOS (with PowerShell installed):**

```bash
pwsh ./src/Build-Corpus.ps1
```

To refresh webpage snapshots before building, run `python src/refresh_webpages.py` (or `python3` on macOS). Refreshing requires network access; the saved snapshots allow offline rebuilding.

### 3. Start Beacon BOT

**Windows:** Double-click `Start-Beacon.cmd`, or run:

```powershell
.\src\Start-Beacon.ps1
```

**macOS:** Run:

```bash
./run-mac.sh beacon
```

Alternatively, `Start-Beacon.command` launches the Python web server directly on macOS, but the corpus must already have been built.

Open **http://127.0.0.1:8765** in a browser. Keep the server process running while using the application.

### 4. Optional: enable LLM-assisted answers

Copy `.env.example` to `.env` and set:

```dotenv
OPENROUTER_API_KEY=your_key_here
LLM_MODEL=openai/gpt-4o-mini
```

An OpenRouter key is **not required** for the baseline retrieval and extractive-answer workflow. Never commit `.env` or an API key to version control. Live model calls may incur provider charges.

## Example questions

- What is the Sustainable Solutions Lab, and what does it focus on?
- What does SSL research say about climate resilience in Boston?
- Which SSL projects involve community engagement?
- What approaches to climate adaptation appear in SSL publications?

Answers depend on the content and freshness of the locally indexed sources. Source citations should be reviewed before relying on an answer for research or decision-making.

## Evaluation and recorded results

The repository includes reproducible benchmark datasets, generated outputs, automated scoring, and external review materials. The **recorded project snapshots** report:

| Evaluation | Recorded result |
| --- | --- |
| Indexed corpus | 20 sources: 15 PDFs and 5 webpage snapshots |
| Searchable passages | 2,354 chunks |
| Official 10-question benchmark | Citation requirement met on 10/10; preferred source in top five on 10/10 |
| Expanded 50-question benchmark | Citation requirement met on 49/49 expected-supported questions; preferred source in top five on 50/50 |
| All-PDF benchmark | Citation requirement met on 52/52 expected-supported questions; preferred source in top five on 53/53 |
| Human review (20 questions) | Mean answer quality 4.15/5, grounding 4.10/5, helpfulness 4.05/5 |

**Interpretation:** Citation presence, expected-support matches, and preferred-source retrieval are **benchmark checks**, not proof that all generated answers are factually correct. The human review also identified questions requiring improvement. These are stored results from the repository, not independently rerun measurements.

See:

- [`eval/phase1_metrics.md`](eval/phase1_metrics.md)
- [`eval/question_coverage_50_summary.md`](eval/question_coverage_50_summary.md)
- [`eval/manualscoring1_summary.md`](eval/manualscoring1_summary.md)
- [`docs/failure_analysis.md`](docs/failure_analysis.md)
- [`docs/metrics_visuals.html`](docs/metrics_visuals.html)

### Run a benchmark

```powershell
.\src\Run-Demo.ps1 -QuestionsPath "eval/question_coverage_50.json"
```

### Compute text-based metrics

```bash
python src/eval_text_metrics.py --results-md eval/phase2_eval_32_candidate_results.md --out-json eval/text_metrics_phase2.json
```

This evaluation script supports metrics including ROUGE, BERTScore, exact match, and token-level F1. Reference answers are needed for meaningful text-comparison metrics.

### Run LLM-as-judge evaluation

```powershell
.\src\Run-LLM-Judge-Jury.ps1 -Mock -Limit 3
```

The mock mode checks the evaluation workflow without making live model requests. Live scoring requires configuration through `.env`; see the existing scripts and `docs/command_key.txt` for more options.

## Design choices and limitations

- **Evidence first:** Retrieval and citations are central to the system, rather than unrestricted general-purpose chat.
- **Lexical retrieval:** The baseline uses a BM25-style index; it is not a vector-embedding or fine-tuned retrieval model.
- **Optional generation:** LLM responses are constrained by retrieved passages, but can still be incomplete or inaccurate.
- **Snapshot freshness:** Some indexed webpage content is saved locally and may not reflect current SSL information until refreshed and rebuilt.
- **Evaluation scope:** Benchmark results reflect the supplied questions, corpus, and evaluation procedures; they should not be treated as general accuracy guarantees.
- **Local prototype:** The included server is intended for local use and demonstration, not a production-hardened public deployment.

## Project background

Beacon BOT was developed as part of a **CS 438/638 team project** focused on improving access to public Sustainable Solutions Lab research materials. The repository also documents subsequent evaluation and refinement work, including expanded question coverage, partner review, and analysis of answer failures.

## Acknowledgments

Developed for the Sustainable Solutions Lab research-assistant project at the **University of Massachusetts Boston**. The repository includes team project work, SSL public source materials, and feedback/evaluation documents. Refer to the project materials for individual team contributions and reviewer attribution.
