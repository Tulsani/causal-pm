from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_SRC = REPO_ROOT / "services" / "causal-engine" / "src"
sys.path.insert(0, str(ENGINE_SRC))

from causal_pm_engine.synerise import _json_default, run_analysis  # noqa: E402


def _parse_sample_sizes(values: list[str]) -> list[int]:
    sample_sizes: list[int] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                sample_sizes.append(int(part))
    return sample_sizes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run reproducible Synerise causal-engine experiments."
    )
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data" / "archive")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "experiments" / "runs")
    parser.add_argument("--sample-sizes", nargs="+", default=["5000", "50000", "100000"])
    parser.add_argument("--train-fraction", type=float, default=0.7)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--label", default="synerise")
    args = parser.parse_args()

    sample_sizes = _parse_sample_sizes(args.sample_sizes)
    if not sample_sizes:
        raise SystemExit("At least one sample size is required.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "label": args.label,
        "timestamp": timestamp,
        "data_dir": str(args.data_dir),
        "train_fraction": args.train_fraction,
        "seed": args.seed,
        "runs": [],
    }

    for sample_size in sample_sizes:
        output_path = args.output_dir / f"{args.label}_{sample_size}_{timestamp}.json"
        print(f"Running sample_size={sample_size} -> {output_path}")
        result = run_analysis(
            data_dir=args.data_dir,
            max_clients=sample_size,
            train_fraction=args.train_fraction,
            seed=args.seed,
            treatments=["search_query", "add_to_cart", "remove_from_cart"],
        )
        output_path.write_text(
            json.dumps(result, indent=2, default=_json_default) + "\n",
            encoding="utf-8",
        )
        manifest["runs"].append(
            {
                "sample_size": sample_size,
                "output": str(output_path),
                "clients_with_post_purchase": result["dataset"]["clients_with_post_purchase"],
            }
        )

    manifest_path = args.output_dir / f"{args.label}_manifest_{timestamp}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote manifest -> {manifest_path}")


if __name__ == "__main__":
    main()

