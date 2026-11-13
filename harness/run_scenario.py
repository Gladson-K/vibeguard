"""Drive a scenario against a running gateway and assert acceptance metrics."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from harness.metrics import check_expectations, evaluate
from harness.profiles import resolve_scenario
from harness.sources.python_node import PythonNodeSource
from harness.sources.sil import SilSource
from harness.transport import HttpTransport

ROOT = Path(__file__).resolve().parents[1]


def build_source(scenario: dict, source: str, sil_binary: str | None, model_path: str | None):
    if source == "sil":
        if not sil_binary:
            raise ValueError("--sil-binary is required for --source sil")
        return SilSource(scenario, sil_binary)
    model = None
    if scenario.get("version") == "v2":
        from harness.model import TinyMLModel

        model = TinyMLModel.load(model_path or ROOT / "models" / "tinyml" / "model.json")
    return PythonNodeSource(scenario, model)


def run_scenario(
    scenario_path: str | Path,
    url: str,
    source: str = "python",
    sil_binary: str | None = None,
    model_path: str | None = None,
    report_dir: str | Path | None = None,
    verbose: bool = True,
) -> tuple[dict, list[str]]:
    scenario = resolve_scenario(scenario_path)
    device = scenario["device_id"]
    transport = HttpTransport(url)
    transport.reset(device)

    src = build_source(scenario, source, sil_binary, model_path)
    statuses: list[str] = []
    latencies: list[float] = []
    scores: list[float | None] = []
    for frame in src.frames():
        res, dt = transport.send(frame)
        statuses.append(res["status"])
        latencies.append(dt)
        scores.append(frame.get("model_score"))
        if verbose and res["status"] == "anomaly":
            print(f"[{scenario['name']}] anomaly at window {len(statuses) - 1} ({res})")

    baseline_windows = int(scenario.get("baseline_windows", 60))
    metrics = evaluate(statuses, latencies, scenario.get("fault_after"), baseline_windows)
    failures = check_expectations(metrics, scenario.get("expect", {}))
    result = {
        "scenario": scenario["name"],
        "version": scenario.get("version", "v1"),
        "device_id": device,
        "source": source,
        **metrics.as_dict(),
        "expect": scenario.get("expect", {}),
        "failures": failures,
    }

    if report_dir is not None:
        out = Path(report_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{scenario['name']}.json").write_text(json.dumps(result, indent=2))
    if verbose:
        print(json.dumps(result, indent=2))
    return result, failures


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", required=True)
    p.add_argument("--url", default=os.environ.get("GATEWAY_URL", "http://localhost:8000"))
    p.add_argument("--source", default="python", choices=["python", "sil"])
    p.add_argument("--sil-binary", default=os.environ.get("VG_SIL_BIN"))
    p.add_argument("--model", default=None)
    p.add_argument("--report-dir", default=os.environ.get("VG_REPORT_DIR", "reports"))
    p.add_argument("--quiet", action="store_true")
    a = p.parse_args(argv)

    _, failures = run_scenario(
        a.scenario, a.url, a.source, a.sil_binary, a.model, a.report_dir, not a.quiet
    )
    if failures:
        print("FAILED:", "; ".join(failures), file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
