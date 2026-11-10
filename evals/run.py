"""Run the eval set against one or more models and write a comparison report.

Usage:
    python -m evals.run                                  # default model
    python -m evals.run claude-haiku-5-5 claude-opus-5-5 # compare models

Output: evals/results/<timestamp>_<model>.json (every case, every reply) and evals/results/REPORT.md.
Needs ANTHROPIC_API_KEY in the environment or in .env.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.core import DEFAULT_MODEL, respond  # noqa: E402
from evals.grader import grade  # noqa: E402

RESULTS = ROOT / "evals" / "results"


def run_model(model: str, data: dict) -> dict:
    rows, cost, seconds = [], 0.0, 0.0
    for case in data["cases"]:
        history, replies, steps, sent = [], [], [], []
        for turn in case["turns"]:
            r = respond(history + [{"role": "user", "content": turn}], model=model, today=data["today"])
            sent += [m for m in r["history"] if m["role"] == "user"]
            history = r["history"]
            replies.append(r["text"])
            steps += r["steps"]
            cost += r["cost_usd"]
            seconds += r["seconds"]
        passed, reason = grade(case, replies, steps, sent)
        rows.append({"id": case["id"], "category": case["category"], "passed": passed, "reason": reason,
                     "turns": case["turns"], "replies": replies, "tools": [s["tool"] for s in steps]})
        print(f"{'PASS' if passed else 'FAIL'} {case['id']:>2} {case['category']:<16} {reason:<34} {case['turns'][0][:50]}", flush=True)
    ok = sum(r["passed"] for r in rows)
    return {"model": model, "passed": ok, "total": len(rows), "cost_usd": round(cost, 4),
            "avg_seconds": round(seconds / len(rows), 2), "rows": rows}


def write_report(runs: list[dict]) -> Path:
    lines = [f"# Eval report — {datetime.now():%Y-%m-%d %H:%M}", "",
             "| Model | Passed | Rate | Cost (USD) | Avg s/case |", "|---|---|---|---|---|"]
    for r in runs:
        lines.append(f"| {r['model']} | {r['passed']}/{r['total']} | {r['passed'] / r['total']:.0%} | {r['cost_usd']:.4f} | {r['avg_seconds']} |")
    lines += ["", "## Pass rate by category", "", "| Category | " + " | ".join(r["model"] for r in runs) + " |",
              "|---" * (len(runs) + 1) + "|"]
    categories = list(dict.fromkeys(row["category"] for row in runs[0]["rows"]))
    for cat in categories:
        cells = []
        for r in runs:
            c = Counter(row["passed"] for row in r["rows"] if row["category"] == cat)
            cells.append(f"{c[True]}/{c[True] + c[False]}")
        lines.append(f"| {cat} | " + " | ".join(cells) + " |")
    lines += ["", "## Failures", ""]
    for r in runs:
        fails = [row for row in r["rows"] if not row["passed"]]
        lines.append(f"### {r['model']}" + (" — none" if not fails else ""))
        for row in fails:
            reply = row["replies"][-1].replace("\n", " ")[:220]
            lines.append(f"- **#{row['id']} ({row['category']})** — {row['reason']}. Input: _{row['turns'][-1]}_. Reply: \"{reply}\"")
        lines.append("")
    path = RESULTS / "REPORT.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main():
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    models = sys.argv[1:] or [DEFAULT_MODEL]
    data = json.loads((ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))
    RESULTS.mkdir(exist_ok=True)
    runs = []
    for model in models:
        print(f"\n== {model} ==")
        run = run_model(model, data)
        print(f"{run['passed']}/{run['total']} · US$ {run['cost_usd']} · {run['avg_seconds']} s/case")
        (RESULTS / f"{datetime.now():%Y%m%d-%H%M}_{model}.json").write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
        runs.append(run)
    print("\nReport:", write_report(runs))


if __name__ == "__main__":
    main()
