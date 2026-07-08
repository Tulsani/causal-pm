from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


METRICS = (
    ("naive", "naive_risk_difference"),
    ("activity", "activity_adjusted_risk_difference"),
    ("propensity", "propensity_proxy_adjusted_risk_difference"),
    ("regression", "regression_adjusted_risk_difference"),
)


def _percent(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value) * 100:+.2f}%"
    except (TypeError, ValueError):
        return "n/a"


def _weight(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return "n/a"


def _load_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows_for_result(path: Path, result: dict[str, Any]) -> list[dict[str, str]]:
    dataset = result.get("dataset", {})
    rows: list[dict[str, str]] = []
    for effect in result.get("effects", []):
        row = {
            "file": path.name,
            "clients": str(dataset.get("sampled_clients", "n/a")),
            "post_buyers": str(dataset.get("clients_with_post_purchase", "n/a")),
            "treatment": effect.get("treatment", "n/a"),
            "treated": str(effect.get("treated_clients", "n/a")),
            "control": str(effect.get("control_clients", "n/a")),
        }
        for label, key in METRICS:
            row[label] = _percent(effect.get(key))
        row["activity_wt"] = _weight(effect.get("activity_included_weight"))
        row["propensity_wt"] = _weight(effect.get("propensity_proxy_included_weight"))
        rows.append(row)
    return rows


def _print_table(rows: list[dict[str, str]]) -> None:
    if not rows:
        print("No effects found.")
        return

    columns = [
        "file",
        "clients",
        "post_buyers",
        "treatment",
        "treated",
        "control",
        "naive",
        "activity",
        "activity_wt",
        "propensity",
        "propensity_wt",
        "regression",
    ]
    widths = {
        column: max(len(column), *(len(row[column]) for row in rows))
        for column in columns
    }

    header = "  ".join(column.ljust(widths[column]) for column in columns)
    separator = "  ".join("-" * widths[column] for column in columns)
    print(header)
    print(separator)
    for row in rows:
        print("  ".join(row[column].ljust(widths[column]) for column in columns))


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Synerise causal result JSON files.")
    parser.add_argument("results", type=Path, nargs="+")
    args = parser.parse_args()

    rows: list[dict[str, str]] = []
    for path in args.results:
        result = _load_result(path)
        rows.extend(_rows_for_result(path, result))

    _print_table(rows)


if __name__ == "__main__":
    main()
