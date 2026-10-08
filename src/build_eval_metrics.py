"""Merge live multiturn API metrics and regression-spec summaries into eval/metrics_snapshot.json.

Refreshes the embedded JSON in docs/metrics_visuals.html unless --no-embed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "eval" / "metrics_snapshot.json"
MULTITURN_METRICS_PATH = ROOT / "eval" / "multiturn_metrics.json"
MULTITURN_SPEC_PATH = ROOT / "eval" / "multiturn_regression_sample.json"
TRICKY_SPEC_PATH = ROOT / "eval" / "regression_tricky_prompts.json"
EMBED_SCRIPT = ROOT / "docs" / "regenerate_metrics_embed.py"

TEXT_METRIC_RUNS: tuple[tuple[str, str, str], ...] = (
    (
        "phase2_eval_32_candidate",
        "Phase 2 candidate (32)",
        "eval/text_metrics_phase2_eval_32_candidate.json",
    ),
    (
        "question_coverage_50",
        "Expanded coverage (50)",
        "eval/text_metrics_question_coverage_50.json",
    ),
)

CHAIN_LABELS: dict[str, str] = {
    "chain_focus_funding": "Focus → funding follow-ups",
    "chain_focus_alt_phrasing": "Short focus → grants",
    "chain_director": "Director phrasing variants",
    "chain_staff_roles": "Staff and roles (deep chain)",
    "chain_wording_variants": "Casual / lowercase phrasing",
    "chain_oos_then_recover": "OOS guardrail → recovery",
}

TRICKY_CATEGORY_BUCKETS: dict[str, str] = {
    "overview_refusal": "Expected refusal / OOS",
    "opportunity_refusal": "Expected refusal / OOS",
    "scope_refusal": "Expected refusal / OOS",
    "research_focus": "Factual / web lookup",
    "people_lookup": "Factual / web lookup",
    "synthesis": "Broad synthesis",
}


def _label_for_chain(chain_id: str) -> str:
    return CHAIN_LABELS.get(
        chain_id,
        chain_id.replace("chain_", "").replace("_", " ").title(),
    )


def build_regression_coverage(root: Path) -> dict | None:
    """Summarize multiturn JSON spec and tricky regression prompts for metrics visuals."""
    mt_path = root / "eval" / "multiturn_regression_sample.json"
    tr_path = root / "eval" / "regression_tricky_prompts.json"
    if not mt_path.is_file() and not tr_path.is_file():
        return None

    out: dict = {}

    if mt_path.is_file():
        spec = json.loads(mt_path.read_text(encoding="utf-8"))
        chains_raw = spec.get("chains") or []
        chains_out: list[dict] = []
        total_turns = 0
        total_guard = 0
        for ch in chains_raw:
            cid = str(ch.get("id") or "")
            turns = ch.get("turns") or []
            n_turns = len(turns)
            n_guard = sum(1 for t in turns if isinstance(t, dict) and t.get("expect_guardrail"))
            total_turns += n_turns
            total_guard += n_guard
            chains_out.append(
                {
                    "id": cid,
                    "label": _label_for_chain(cid),
                    "turns": n_turns,
                    "guardrail_turns": n_guard,
                }
            )
        out["multiturn_spec"] = str(mt_path.relative_to(root)).replace("\\", "/")
        out["multiturn"] = {
            "chains": chains_out,
            "totals": {
                "chains": len(chains_out),
                "turns": total_turns,
                "guardrail_turns": total_guard,
                "content_checks": total_turns - total_guard,
            },
        }

    if tr_path.is_file():
        rows = json.loads(tr_path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            rows = []
        bucket_counts: Counter[str] = Counter()
        for row in rows:
            if not isinstance(row, dict):
                continue
            cat = str(row.get("category") or "uncategorized")
            bucket = TRICKY_CATEGORY_BUCKETS.get(cat, cat.replace("_", " ").title())
            bucket_counts[bucket] += 1
        by_bucket = [{"label": lab, "count": c} for lab, c in sorted(bucket_counts.items(), key=lambda x: (-x[1], x[0]))]
        out["tricky_prompts_spec"] = str(tr_path.relative_to(root)).replace("\\", "/")
        out["tricky_prompts"] = {
            "total": len(rows),
            "by_bucket": by_bucket,
        }

    return out or None


def merge_text_metrics(root: Path, data: dict) -> None:
    """Attach ROUGE / BERTScore summaries from eval_text_metrics JSON outputs.

    For each run id, a metrics JSON file on disk wins; otherwise any existing
    snapshot entry for that id is kept so a missing local file does not drop
    the 50-set row after a fresh clone.
    """
    prior_runs = (data.get("text_metrics") or {}).get("runs") or []
    by_id: dict[str, dict] = {}
    for row in prior_runs:
        if isinstance(row, dict) and row.get("id"):
            by_id[str(row["id"])] = row

    for run_id, label, rel in TEXT_METRIC_RUNS:
        path = root / Path(rel)
        if not path.is_file():
            continue
        blob = json.loads(path.read_text(encoding="utf-8"))
        summ = blob.get("summary")
        if not isinstance(summ, dict):
            continue
        by_id[run_id] = {
            "id": run_id,
            "label": label,
            "metrics_json": rel,
            "summary": {
                "count": summ.get("count"),
                "rouge1_f1": summ.get("rouge1_f1"),
                "rouge2_f1": summ.get("rouge2_f1"),
                "rougeL_f1": summ.get("rougeL_f1"),
                "bertscore_f1": summ.get("bertscore_f1"),
                "exact_match": summ.get("exact_match"),
                "token_f1": summ.get("token_f1"),
            },
        }

    ordered = [by_id[rid] for rid, _, _ in TEXT_METRIC_RUNS if rid in by_id]
    if ordered:
        data["text_metrics"] = {"runs": ordered}
    elif "text_metrics" not in data:
        data["text_metrics"] = None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--multiturn-metrics",
        type=Path,
        default=MULTITURN_METRICS_PATH,
        help="Path to multiturn_metrics.json (from run_multiturn_regression.py)",
    )
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="Do not run docs/regenerate_metrics_embed.py after updating the snapshot",
    )
    args = parser.parse_args()

    if not SNAPSHOT_PATH.is_file():
        print(f"Missing snapshot: {SNAPSHOT_PATH}", file=sys.stderr)
        return 1

    data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    mt_path: Path = args.multiturn_metrics
    if mt_path.is_file():
        data["live_multiturn"] = json.loads(mt_path.read_text(encoding="utf-8"))
        print(f"Merged live_multiturn from {mt_path.relative_to(ROOT)}")
    else:
        data["live_multiturn"] = None
        print(f"No {mt_path.relative_to(ROOT)}; set live_multiturn to null")

    rc = build_regression_coverage(ROOT)
    if rc is not None:
        data["regression_coverage"] = rc
        print("Wrote regression_coverage from multiturn + tricky JSON specs")
    else:
        data["regression_coverage"] = None
        print("No multiturn/tricky spec JSON; regression_coverage set to null")

    merge_text_metrics(ROOT, data)
    if data.get("text_metrics"):
        print("Merged text_metrics from eval/text_metrics_*.json (where present)")

    sources = list(dict.fromkeys(str(p).replace("\\", "/") for p in (data.get("sources") or [])))
    rel_mt = str(mt_path.relative_to(ROOT)).replace("\\", "/")
    if rel_mt not in sources:
        sources.append(rel_mt)
    for extra in (
        str(MULTITURN_SPEC_PATH.relative_to(ROOT)).replace("\\", "/"),
        str(TRICKY_SPEC_PATH.relative_to(ROOT)).replace("\\", "/"),
        "eval/text_metrics_phase2_eval_32_candidate.json",
        "eval/text_metrics_question_coverage_50.json",
    ):
        if Path(ROOT / extra).is_file() and extra not in sources:
            sources.append(extra)
    data["sources"] = sources

    SNAPSHOT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {SNAPSHOT_PATH.relative_to(ROOT)}")

    if not args.no_embed:
        if not EMBED_SCRIPT.is_file():
            print(f"Skip embed: missing {EMBED_SCRIPT}", file=sys.stderr)
            return 0
        r = subprocess.run([sys.executable, str(EMBED_SCRIPT)], cwd=str(ROOT), check=False)
        if r.returncode != 0:
            print(f"embed script exited {r.returncode}", file=sys.stderr)
            return r.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
