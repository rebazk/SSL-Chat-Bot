from __future__ import annotations

import argparse
import json
import re
import string
from collections import Counter
from pathlib import Path

from bert_score import score as bert_score
from rouge_score import rouge_scorer


def _normalize_text(text: str) -> str:
    lowered = text.lower()
    no_punct = "".join(ch for ch in lowered if ch not in string.punctuation)
    compact = " ".join(no_punct.split())
    return compact


def _exact_match(reference: str, prediction: str) -> float:
    return 1.0 if _normalize_text(reference) == _normalize_text(prediction) else 0.0


def _token_f1(reference: str, prediction: str) -> float:
    ref_tokens = _normalize_text(reference).split()
    pred_tokens = _normalize_text(prediction).split()
    if not ref_tokens and not pred_tokens:
        return 1.0
    if not ref_tokens or not pred_tokens:
        return 0.0

    overlap = Counter(ref_tokens) & Counter(pred_tokens)
    common = sum(overlap.values())
    if common == 0:
        return 0.0
    precision = common / len(pred_tokens)
    recall = common / len(ref_tokens)
    return 2 * precision * recall / (precision + recall)


def _extract_section_value(section: str, heading: str, next_headings: list[str]) -> str:
    escaped_heading = re.escape(heading)
    stop_pattern = "|".join(re.escape(h) for h in next_headings)
    pattern = rf"{escaped_heading}\n(.*?)(?:\n(?:{stop_pattern})|\Z)"
    match = re.search(pattern, section, flags=re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def load_reference_map(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return {}
    refs: dict[str, str] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        ref = str(row.get("reference_answer") or "").strip()
        if not ref:
            continue
        row_id = str(row.get("id") or "").strip()
        source_id = str(row.get("source_question_id") or "").strip()
        if row_id:
            refs[row_id] = ref
        if source_id:
            refs[source_id] = ref
    return refs


def merge_reference_maps(paths: list[Path]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in paths:
        merged.update(load_reference_map(path))
    return merged


def parse_results_markdown(path: Path, reference_map: dict[str, str] | None = None) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"\n## ", text)
    rows: list[dict[str, str]] = []
    refs = reference_map or {}
    for section in sections[1:]:
        header, _, body = section.partition("\n")
        question_id = header.split(":", 1)[0].strip()
        reference = _extract_section_value(
            body,
            "Reference answer:",
            ["Answer:", "Top retrieval results:", "## "],
        )
        answer = _extract_section_value(
            body,
            "Answer:",
            ["Citations:", "Top retrieval results:", "## "],
        )
        if not reference:
            reference = refs.get(question_id, "")
        if reference and answer:
            rows.append({"id": question_id, "reference": reference, "prediction": answer})
    return rows


def evaluate_rows(rows: list[dict[str, str]], bert_lang: str = "en") -> dict:
    if not rows:
        raise ValueError("No comparable rows found. Ensure the markdown has Reference answer and Answer blocks.")

    references = [row["reference"] for row in rows]
    predictions = [row["prediction"] for row in rows]

    rouge = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    rouge1_scores: list[float] = []
    rouge2_scores: list[float] = []
    rougeL_scores: list[float] = []
    em_scores: list[float] = []
    f1_scores: list[float] = []

    for ref, pred in zip(references, predictions):
        score = rouge.score(ref, pred)
        rouge1_scores.append(score["rouge1"].fmeasure)
        rouge2_scores.append(score["rouge2"].fmeasure)
        rougeL_scores.append(score["rougeL"].fmeasure)
        em_scores.append(_exact_match(ref, pred))
        f1_scores.append(_token_f1(ref, pred))

    _, _, bert_f1 = bert_score(predictions, references, lang=bert_lang, verbose=False)
    bert_scores = [float(v) for v in bert_f1]

    per_question = []
    for idx, row in enumerate(rows):
        per_question.append(
            {
                "id": row["id"],
                "rouge1_f1": round(rouge1_scores[idx], 4),
                "rouge2_f1": round(rouge2_scores[idx], 4),
                "rougeL_f1": round(rougeL_scores[idx], 4),
                "bertscore_f1": round(bert_scores[idx], 4),
                "exact_match": round(em_scores[idx], 4),
                "token_f1": round(f1_scores[idx], 4),
            }
        )

    return {
        "summary": {
            "count": len(rows),
            "rouge1_f1": round(sum(rouge1_scores) / len(rouge1_scores), 4),
            "rouge2_f1": round(sum(rouge2_scores) / len(rouge2_scores), 4),
            "rougeL_f1": round(sum(rougeL_scores) / len(rougeL_scores), 4),
            "bertscore_f1": round(sum(bert_scores) / len(bert_scores), 4),
            "exact_match": round(sum(em_scores) / len(em_scores), 4),
            "token_f1": round(sum(f1_scores) / len(f1_scores), 4),
        },
        "per_question": per_question,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute ROUGE, BERTScore, and QA exact-match/F1 from benchmark markdown outputs."
    )
    parser.add_argument(
        "--results-md",
        type=Path,
        default=Path("eval/phase2_eval_32_candidate_results.md"),
        help="Markdown produced by src/Run-Demo.ps1 (default: eval/phase2_eval_32_candidate_results.md).",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=Path("eval/text_metrics_phase2.json"),
        help="Output JSON path for metric summary and per-question scores.",
    )
    parser.add_argument(
        "--bert-lang",
        default="en",
        help="Language code for BERTScore model selection (default: en).",
    )
    parser.add_argument(
        "--reference-json",
        type=Path,
        nargs="+",
        default=None,
        help="Optional one-or-more JSON files containing reference_answer values keyed by id/source_question_id.",
    )
    args = parser.parse_args()

    reference_map = merge_reference_maps(args.reference_json) if args.reference_json else None
    rows = parse_results_markdown(args.results_md, reference_map=reference_map)
    metrics = evaluate_rows(rows, bert_lang=args.bert_lang)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote metrics for {metrics['summary']['count']} items -> {args.out_json}")
    print("Summary:")
    for key, value in metrics["summary"].items():
        if key == "count":
            continue
        print(f"- {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
