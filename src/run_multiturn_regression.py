from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path


def _post_json(url: str, payload: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body or "{}")


def _evaluate_turn(answer_payload: dict, turn_spec: dict) -> tuple[bool, str]:
    expected_guardrail = str(turn_spec.get("expect_guardrail") or "").strip()
    if expected_guardrail:
        got = str(answer_payload.get("guardrail") or "")
        ok = got == expected_guardrail
        return ok, f"guardrail expected={expected_guardrail} got={got or '<none>'}"

    answer_text = str(answer_payload.get("answer") or "").lower()
    contains_any = turn_spec.get("expect_contains_any") or []
    if contains_any:
        options = [str(x).lower() for x in contains_any]
        ok = any(opt in answer_text for opt in options)
        return ok, f"contains any of {contains_any}"

    return True, "no explicit expectation"


def _latency_summary_ms(samples: list[float]) -> dict[str, float]:
    if not samples:
        return {"mean": 0.0, "p50": 0.0, "p95": 0.0, "min": 0.0, "max": 0.0}
    s = sorted(samples)

    def _pct(p: float) -> float:
        if len(s) == 1:
            return float(s[0])
        rank = (len(s) - 1) * (p / 100.0)
        lo = int(rank)
        hi = min(lo + 1, len(s) - 1)
        frac = rank - lo
        return float(s[lo] + (s[hi] - s[lo]) * frac)

    return {
        "mean": round(float(statistics.mean(s)), 2),
        "p50": round(_pct(50.0), 2),
        "p95": round(_pct(95.0), 2),
        "min": round(float(s[0]), 2),
        "max": round(float(s[-1]), 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run multi-turn Beacon BOT regression checks.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765", help="Beacon BOT base URL")
    parser.add_argument(
        "--input",
        default="eval/multiturn_regression_sample.json",
        help="Path to regression JSON with chain definitions",
    )
    parser.add_argument(
        "--output",
        default="eval/multiturn_regression_results.md",
        help="Path to markdown output report",
    )
    parser.add_argument("--timeout-sec", type=float, default=45.0, help="Per-request timeout")
    parser.add_argument(
        "--metrics-out",
        type=Path,
        default=Path("eval/multiturn_metrics.json"),
        help="Write per-run API latency and pass stats for metrics_visuals (default: eval/multiturn_metrics.json)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    spec = json.loads(input_path.read_text(encoding="utf-8"))
    chains = spec.get("chains") or []

    ask_url = args.base_url.rstrip("/") + "/api/ask"
    rows: list[str] = []
    total_checks = 0
    passed_checks = 0
    latency_ms_samples: list[float] = []
    guardrail_turns = 0
    guardrail_passed = 0
    http_errors = 0

    started = time.time()
    for chain_idx, chain in enumerate(chains):
        chain_id = str(chain.get("id") or f"chain_{chain_idx + 1}")
        session_id = f"mt_reg_{chain_idx + 1}"
        turns = chain.get("turns") or []
        rows.append(f"## {chain_id}")
        rows.append("")
        rows.append("| Turn | Question | Result | Notes |")
        rows.append("|---|---|---|---|")

        for turn_idx, turn in enumerate(turns):
            question = str(turn.get("question") or "").strip()
            if not question:
                rows.append(f"| {turn_idx + 1} | *(empty)* | FAIL | Missing question in spec |")
                total_checks += 1
                continue
            total_checks += 1
            t_req = time.perf_counter()
            try:
                payload = _post_json(
                    ask_url,
                    {"question": question, "top": 5, "session_id": session_id},
                    timeout=args.timeout_sec,
                )
                latency_ms_samples.append((time.perf_counter() - t_req) * 1000.0)
                ok, note = _evaluate_turn(payload, turn)
            except json.JSONDecodeError as exc:
                http_errors += 1
                ok, note = False, f"invalid JSON in response: {exc}"
            except urllib.error.HTTPError as exc:
                http_errors += 1
                detail = ""
                try:
                    raw = exc.read()
                    detail = raw.decode("utf-8", errors="replace").strip()
                except OSError:
                    pass
                if len(detail) > 400:
                    detail = detail[:400] + "..."
                ok, note = False, f"HTTP {exc.code}: {detail or exc.reason or exc}"
            except (urllib.error.URLError, TimeoutError) as exc:
                http_errors += 1
                ok, note = False, f"request failed: {exc}"

            if str(turn.get("expect_guardrail") or "").strip():
                guardrail_turns += 1
                if ok:
                    guardrail_passed += 1

            if ok:
                passed_checks += 1
            status = "PASS" if ok else "FAIL"
            q_disp = question.replace("|", "\\|")
            n_disp = note.replace("|", "\\|")
            rows.append(f"| {turn_idx + 1} | {q_disp} | {status} | {n_disp} |")
        rows.append("")

    elapsed = time.time() - started
    summary = [
        "# Multi-turn Regression Results",
        "",
        f"- Total checks: **{total_checks}**",
        f"- Passed: **{passed_checks}**",
        f"- Failed: **{total_checks - passed_checks}**",
        f"- Pass rate: **{(passed_checks / total_checks * 100.0) if total_checks else 0.0:.1f}%**",
        f"- Elapsed: **{elapsed:.2f}s**",
        "",
    ]

    output_path = Path(args.output)
    output_path.write_text("\n".join(summary + rows), encoding="utf-8")
    print(f"Wrote regression report: {output_path}")

    metrics_path = Path(args.metrics_out)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_url": args.base_url,
        "input": str(Path(args.input).as_posix()),
        "results_md": str(Path(args.output).as_posix()),
        "total_checks": total_checks,
        "passed": passed_checks,
        "failed": total_checks - passed_checks,
        "pass_rate": round(passed_checks / total_checks, 4) if total_checks else 0.0,
        "elapsed_sec": round(elapsed, 3),
        "latency_ms": _latency_summary_ms(latency_ms_samples),
        "latency_sample_count": len(latency_ms_samples),
        "guardrail_turns": guardrail_turns,
        "guardrail_passed": guardrail_passed,
        "http_errors": http_errors,
        "notes": "Latency is round-trip POST /api/ask until JSON parse succeeds; excludes failed requests.",
    }
    metrics_path.write_text(json.dumps(metrics_payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote metrics: {metrics_path}")

    return 0 if passed_checks == total_checks else 1


if __name__ == "__main__":
    raise SystemExit(main())
