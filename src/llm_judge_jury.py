from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_RESULTS_MD = ROOT / "eval" / "manualscoring1_postfix_results.md"
DEFAULT_OUT_JSON = ROOT / "eval" / "llm_jury_manualscoring1_postfix.json"
DEFAULT_OUT_MD = ROOT / "eval" / "llm_jury_manualscoring1_postfix.md"

PERSONAS = (
    {
        "name": "source_grounding_judge",
        "focus": "Be strict about citation/source fit, unsupported claims, and whether the cited evidence could support the answer.",
    },
    {
        "name": "institute_user_judge",
        "focus": "Score from the perspective of an SSL public user trying to find the right page/report or understand SSL research quickly.",
    },
    {
        "name": "clarity_correctness_judge",
        "focus": "Focus on correctness against the reference answer, directness, concision, and whether the response answers the actual question.",
    },
)


@dataclass
class JudgeItem:
    question_id: str
    question: str
    category: str
    question_type: str
    institute_workflow: str
    expected_support: str
    answer_support_status: str
    citation_requirement_met: str
    support_expectation_matched: str
    preferred_source_hit: str
    expected_behavior: str
    reference_answer: str
    answer: str
    citations: list[str]
    top_results: list[str]


def load_dotenv_minimal(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def extract_section_value(section: str, heading: str, next_headings: list[str]) -> str:
    stop = "|".join(re.escape(h) for h in next_headings)
    pattern = rf"{re.escape(heading)}\n(.*?)(?:\n(?:{stop})|\Z)"
    match = re.search(pattern, section, flags=re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_inline_value(section: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}:\s*`?([^`\n]+)`?\s*$", section, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def parse_list_block(text: str) -> list[str]:
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            rows.append(stripped[2:].strip())
    return rows


def parse_results_markdown(path: Path) -> list[JudgeItem]:
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"\n## ", text)
    items: list[JudgeItem] = []
    for section in sections[1:]:
        header, _, body = section.partition("\n")
        if ":" in header:
            question_id, question = header.split(":", 1)
        else:
            question_id, question = header.strip(), ""

        citations_block = extract_section_value(body, "Citations:", ["Top retrieval results:", "## "])
        top_results_block = extract_section_value(body, "Top retrieval results:", ["## "])

        items.append(
            JudgeItem(
                question_id=question_id.strip(),
                question=question.strip(),
                category=extract_inline_value(body, "Category"),
                question_type=extract_inline_value(body, "Question type"),
                institute_workflow=extract_inline_value(body, "Institute workflow"),
                expected_support=extract_inline_value(body, "Expected support"),
                answer_support_status=extract_inline_value(body, "Answer support status"),
                citation_requirement_met=extract_inline_value(body, "Citation requirement met"),
                support_expectation_matched=extract_inline_value(body, "Support expectation matched"),
                preferred_source_hit=extract_inline_value(body, "Preferred source hit in top 5"),
                expected_behavior=extract_section_value(body, "Expected behavior:", ["Reference answer:", "Answer:", "Citations:", "Top retrieval results:", "## "]),
                reference_answer=extract_section_value(body, "Reference answer:", ["Answer:", "Citations:", "Top retrieval results:", "## "]),
                answer=extract_section_value(body, "Answer:", ["Citations:", "Top retrieval results:", "## "]),
                citations=parse_list_block(citations_block),
                top_results=parse_list_block(top_results_block)[:5],
            )
        )
    return items


def make_prompt(item: JudgeItem, persona: dict[str, str]) -> str:
    payload = {
        "question_id": item.question_id,
        "question": item.question,
        "category": item.category,
        "question_type": item.question_type,
        "institute_workflow": item.institute_workflow,
        "expected_support": item.expected_support,
        "pipeline_support_status": item.answer_support_status,
        "pipeline_citation_requirement_met": item.citation_requirement_met,
        "pipeline_support_expectation_matched": item.support_expectation_matched,
        "pipeline_preferred_source_hit": item.preferred_source_hit,
        "expected_behavior": item.expected_behavior,
        "reference_answer": item.reference_answer,
        "answer_to_score": item.answer,
        "citations": item.citations,
        "top_retrieval_results": item.top_results,
    }
    return f"""You are an LLM evaluator for Beacon BOT, a citation-first assistant over public Sustainable Solutions Lab (SSL) materials.

Judge persona: {persona["name"]}
Judge focus: {persona["focus"]}

Score the answer using this rubric:
- answer_quality_1_5: factual/direct answer quality vs the question and reference.
- grounding_quality_1_5: whether the answer is supported by citations/retrieval and avoids unsupported claims.
- helpfulness_1_5: whether a public SSL user would find the answer useful.
- sc1_pass: "Pass", "Fail", or "N/A". SC1 means the user can identify the right SSL page, report, or publication path in one interaction.
- sc2_pass: "Pass", "Fail", or "N/A". SC2 means the user gets a grounded summary of SSL findings/priorities without reading multiple documents.
- citation_ok: boolean. True only if the required citation/source behavior looks acceptable.
- major_issue: boolean. True for non-responsive answers, unsupported answers, wrong source/citation, or severe usefulness problems.

Return only a compact JSON object with exactly these keys:
answer_quality_1_5, grounding_quality_1_5, helpfulness_1_5, sc1_pass, sc2_pass, citation_ok, major_issue, rationale, recommended_fix

Keep rationale and recommended_fix each under 35 words. Use only the evidence below.

Evaluation item:
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""


def post_openrouter(api_key: str, model: str, prompt: str, timeout: int) -> str:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 260,
    }
    request = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/",
            "X-Title": "SSL Beacon BOT LLM Judge Jury",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return str(data["choices"][0]["message"]["content"]).strip()


def parse_judge_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        data = json.loads(match.group(0))
    return normalize_judge_row(data)


def clamp_int(value: Any, low: int = 1, high: int = 5) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = low
    return max(low, min(high, number))


def normalize_pass(value: Any) -> str:
    text = str(value or "N/A").strip().upper()
    if text.startswith("PASS"):
        return "Pass"
    if text.startswith("FAIL"):
        return "Fail"
    return "N/A"


def normalize_judge_row(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "answer_quality_1_5": clamp_int(data.get("answer_quality_1_5")),
        "grounding_quality_1_5": clamp_int(data.get("grounding_quality_1_5")),
        "helpfulness_1_5": clamp_int(data.get("helpfulness_1_5")),
        "sc1_pass": normalize_pass(data.get("sc1_pass")),
        "sc2_pass": normalize_pass(data.get("sc2_pass")),
        "citation_ok": bool(data.get("citation_ok")),
        "major_issue": bool(data.get("major_issue")),
        "rationale": str(data.get("rationale") or "").strip()[:500],
        "recommended_fix": str(data.get("recommended_fix") or "").strip()[:500],
    }


def mock_judge(item: JudgeItem, persona: dict[str, str]) -> dict[str, Any]:
    citation_yes = item.citation_requirement_met.lower() == "yes" or item.expected_support == "unsupported"
    support_yes = item.support_expectation_matched.lower() == "yes"
    preferred_yes = item.preferred_source_hit.lower() in ("yes", "")
    answer_quality = 5 if support_yes else 2
    grounding = 5 if citation_yes and preferred_yes else 3
    helpfulness = 5 if answer_quality >= 4 and grounding >= 4 else 3
    major_issue = not (citation_yes and support_yes)
    if "generic SSL overview" in item.answer.lower():
        answer_quality = grounding = helpfulness = 2
        major_issue = True
    return {
        "answer_quality_1_5": answer_quality,
        "grounding_quality_1_5": grounding,
        "helpfulness_1_5": helpfulness,
        "sc1_pass": "Pass" if citation_yes and preferred_yes else "Fail",
        "sc2_pass": "Pass" if support_yes and answer_quality >= 4 else "Fail",
        "citation_ok": citation_yes,
        "major_issue": major_issue,
        "rationale": f"Mock {persona['name']} used existing benchmark flags; run without --mock for real LLM judgment.",
        "recommended_fix": "" if not major_issue else "Inspect citation/source fit and answer responsiveness.",
    }


def majority_pass(values: list[str]) -> str:
    filtered = [v for v in values if v in ("Pass", "Fail")]
    if not filtered:
        return "N/A"
    return "Pass" if filtered.count("Pass") >= filtered.count("Fail") else "Fail"


def aggregate_judgments(judgments: list[dict[str, Any]]) -> dict[str, Any]:
    if not judgments:
        return {}
    answer_scores = [int(j["answer_quality_1_5"]) for j in judgments]
    grounding_scores = [int(j["grounding_quality_1_5"]) for j in judgments]
    helpfulness_scores = [int(j["helpfulness_1_5"]) for j in judgments]
    return {
        "answer_quality_avg": round(statistics.mean(answer_scores), 2),
        "grounding_quality_avg": round(statistics.mean(grounding_scores), 2),
        "helpfulness_avg": round(statistics.mean(helpfulness_scores), 2),
        "answer_quality_median": statistics.median(answer_scores),
        "grounding_quality_median": statistics.median(grounding_scores),
        "helpfulness_median": statistics.median(helpfulness_scores),
        "sc1_pass": majority_pass([j["sc1_pass"] for j in judgments]),
        "sc2_pass": majority_pass([j["sc2_pass"] for j in judgments]),
        "citation_ok": sum(1 for j in judgments if j["citation_ok"]) >= (len(judgments) / 2),
        "major_issue": sum(1 for j in judgments if j["major_issue"]) >= (len(judgments) / 2),
    }


def evaluate_items(
    items: list[JudgeItem],
    *,
    api_key: str | None,
    models: list[str],
    jury_size: int,
    timeout: int,
    sleep_seconds: float,
    mock: bool,
) -> list[dict[str, Any]]:
    rows = []
    for index, item in enumerate(items, start=1):
        judgments = []
        for juror_index in range(jury_size):
            persona = PERSONAS[juror_index % len(PERSONAS)]
            model = models[juror_index % len(models)]
            base = {
                "juror": juror_index + 1,
                "persona": persona["name"],
                "model": model,
            }
            if mock:
                judgment = mock_judge(item, persona)
            else:
                prompt = make_prompt(item, persona)
                try:
                    raw = post_openrouter(api_key or "", model, prompt, timeout)
                    judgment = parse_judge_json(raw)
                    base["raw_response"] = raw
                except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError, ValueError) as exc:
                    judgment = {
                        "answer_quality_1_5": 1,
                        "grounding_quality_1_5": 1,
                        "helpfulness_1_5": 1,
                        "sc1_pass": "N/A",
                        "sc2_pass": "N/A",
                        "citation_ok": False,
                        "major_issue": True,
                        "rationale": f"Judge call failed: {exc}",
                        "recommended_fix": "Rerun this item or inspect API/model configuration.",
                    }
                    base["error"] = str(exc)
            judgments.append({**base, **judgment})
            if not mock and sleep_seconds > 0:
                time.sleep(sleep_seconds)

        rows.append(
            {
                "question_id": item.question_id,
                "question": item.question,
                "category": item.category,
                "question_type": item.question_type,
                "institute_workflow": item.institute_workflow,
                "pipeline_flags": {
                    "expected_support": item.expected_support,
                    "answer_support_status": item.answer_support_status,
                    "citation_requirement_met": item.citation_requirement_met,
                    "support_expectation_matched": item.support_expectation_matched,
                    "preferred_source_hit": item.preferred_source_hit,
                },
                "aggregate": aggregate_judgments(judgments),
                "judgments": judgments,
            }
        )
        print(f"[{index}/{len(items)}] judged {item.question_id}")
    return rows


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "questions_judged": 0,
            "avg_answer_quality": None,
            "avg_grounding_quality": None,
            "avg_helpfulness": None,
            "major_issue_count": 0,
            "sc1_pass": 0,
            "sc1_fail": 0,
            "sc2_pass": 0,
            "sc2_fail": 0,
        }
    aggregates = [row["aggregate"] for row in rows]
    return {
        "questions_judged": len(rows),
        "avg_answer_quality": round(statistics.mean(a["answer_quality_avg"] for a in aggregates), 2),
        "avg_grounding_quality": round(statistics.mean(a["grounding_quality_avg"] for a in aggregates), 2),
        "avg_helpfulness": round(statistics.mean(a["helpfulness_avg"] for a in aggregates), 2),
        "major_issue_count": sum(1 for a in aggregates if a["major_issue"]),
        "sc1_pass": sum(1 for a in aggregates if a["sc1_pass"] == "Pass"),
        "sc1_fail": sum(1 for a in aggregates if a["sc1_pass"] == "Fail"),
        "sc2_pass": sum(1 for a in aggregates if a["sc2_pass"] == "Pass"),
        "sc2_fail": sum(1 for a in aggregates if a["sc2_pass"] == "Fail"),
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# LLM Judge/Jury Results",
        "",
        f"Input: `{payload['input_results_md']}`",
        f"Mode: `{'mock' if payload['mock'] else 'live'}`",
        f"Jury size: `{payload['jury_size']}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Questions judged | {summary['questions_judged']} |",
        f"| Avg answer quality | {summary['avg_answer_quality']} / 5 |",
        f"| Avg grounding quality | {summary['avg_grounding_quality']} / 5 |",
        f"| Avg helpfulness | {summary['avg_helpfulness']} / 5 |",
        f"| Major issue count | {summary['major_issue_count']} |",
        f"| SC1 pass/fail | {summary['sc1_pass']} / {summary['sc1_fail']} |",
        f"| SC2 pass/fail | {summary['sc2_pass']} / {summary['sc2_fail']} |",
        "",
        "## Priority Items",
        "",
    ]
    priority = [row for row in payload["rows"] if row["aggregate"].get("major_issue")]
    if not priority:
        lines.append("No majority-major issues found by the jury.")
    else:
        lines.extend(["| Question | Category | Issue | Suggested fix |", "|---|---|---|---|"])
        for row in priority:
            first_issue = next((j for j in row["judgments"] if j.get("major_issue")), row["judgments"][0])
            lines.append(
                "| {qid} | {cat} | {issue} | {fix} |".format(
                    qid=row["question_id"],
                    cat=row["category"],
                    issue=str(first_issue.get("rationale", "")).replace("|", "\\|"),
                    fix=str(first_issue.get("recommended_fix", "")).replace("|", "\\|"),
                )
            )
    lines.extend(["", "## Per-Question Aggregates", "", "| Question | Answer | Grounding | Helpful | SC1 | SC2 | Major issue |", "|---|---:|---:|---:|---|---|---|"])
    for row in payload["rows"]:
        agg = row["aggregate"]
        lines.append(
            f"| {row['question_id']} | {agg['answer_quality_avg']} | {agg['grounding_quality_avg']} | "
            f"{agg['helpfulness_avg']} | {agg['sc1_pass']} | {agg['sc2_pass']} | {agg['major_issue']} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an LLM judge/jury over Run-Demo benchmark markdown.")
    parser.add_argument("--results-md", type=Path, default=DEFAULT_RESULTS_MD, help="Run-Demo markdown to judge.")
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON, help="Structured JSON output path.")
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD, help="Markdown summary output path.")
    parser.add_argument("--models", nargs="+", default=None, help="OpenRouter model id(s). Multiple models rotate across jurors.")
    parser.add_argument("--jury-size", type=int, default=3, help="Number of jurors per question.")
    parser.add_argument("--limit", type=int, default=None, help="Judge only the first N parsed questions.")
    parser.add_argument("--ids", nargs="+", default=None, help="Judge only these question ids.")
    parser.add_argument("--timeout", type=int, default=60, help="OpenRouter request timeout seconds.")
    parser.add_argument("--sleep-seconds", type=float, default=0.2, help="Pause between live API calls.")
    parser.add_argument("--mock", action="store_true", help="Use deterministic mock judgments; no API key or network needed.")
    return parser.parse_args()


def main() -> int:
    load_dotenv_minimal(ROOT / ".env")
    args = parse_args()
    results_md = resolve_path(args.results_md)
    out_json = resolve_path(args.out_json)
    out_md = resolve_path(args.out_md)
    models = args.models
    if not models:
        env_models = os.getenv("LLM_JURY_MODELS") or os.getenv("LLM_JUDGE_MODEL") or os.getenv("LLM_MODEL") or "openai/gpt-4o-mini"
        models = [model.strip() for model in env_models.split(",") if model.strip()]
    if not models:
        raise SystemExit("No model configured. Pass --models or set LLM_JUDGE_MODEL / LLM_JURY_MODELS.")
    if args.jury_size < 1:
        raise SystemExit("--jury-size must be at least 1")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not args.mock and not api_key:
        raise SystemExit("OPENROUTER_API_KEY is not set. Add .env or rerun with --mock.")

    items = parse_results_markdown(results_md)
    if args.ids:
        wanted = set(args.ids)
        items = [item for item in items if item.question_id in wanted]
    if args.limit is not None:
        items = items[: args.limit]
    if not items:
        raise SystemExit(f"No benchmark items parsed from {results_md}")

    rows = evaluate_items(
        items,
        api_key=api_key,
        models=models,
        jury_size=args.jury_size,
        timeout=args.timeout,
        sleep_seconds=args.sleep_seconds,
        mock=args.mock,
    )
    try:
        input_results_md = str(results_md.relative_to(ROOT))
    except ValueError:
        input_results_md = str(results_md)

    payload = {
        "input_results_md": input_results_md,
        "mock": bool(args.mock),
        "models": models,
        "jury_size": args.jury_size,
        "summary": build_summary(rows),
        "rows": rows,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(out_md, payload)
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
