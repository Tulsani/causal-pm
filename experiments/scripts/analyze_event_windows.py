from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_SRC = REPO_ROOT / "services" / "causal-engine" / "src"
sys.path.insert(0, str(ENGINE_SRC))

from causal_pm_engine.synerise import _json_default, _load_client_sample  # noqa: E402


def _load_events(data_dir: Path, event_file: str, client_ids: set[int]) -> pd.DataFrame:
    parquet = pq.ParquetFile(data_dir / event_file)
    frames: list[pd.DataFrame] = []

    for row_group_idx in range(parquet.metadata.num_row_groups):
        table = parquet.read_row_group(row_group_idx, columns=["client_id", "timestamp", "sku"])
        frame = table.to_pandas()
        frame = frame[frame["client_id"].isin(client_ids)]
        if not frame.empty:
            frames.append(frame)

    if not frames:
        return pd.DataFrame(columns=["client_id", "timestamp", "sku"])

    events = pd.concat(frames, ignore_index=True)
    events["timestamp"] = pd.to_datetime(events["timestamp"])
    return events.sort_values(["timestamp", "client_id", "sku"]).reset_index(drop=True)


def _next_purchase(
    add_to_cart: pd.DataFrame,
    product_buy: pd.DataFrame,
    by: list[str],
    suffix: str,
) -> pd.DataFrame:
    left = add_to_cart.sort_values(["timestamp", *by]).reset_index(drop=True)
    right = product_buy.sort_values(["timestamp", *by]).reset_index(drop=True)
    right = right.rename(columns={"timestamp": f"next_buy_timestamp_{suffix}"})

    merged = pd.merge_asof(
        left,
        right,
        left_on="timestamp",
        right_on=f"next_buy_timestamp_{suffix}",
        by=by,
        direction="forward",
        allow_exact_matches=True,
    )
    merged[f"seconds_to_buy_{suffix}"] = (
        merged[f"next_buy_timestamp_{suffix}"] - merged["timestamp"]
    ).dt.total_seconds()
    return merged


def _window_summary(frame: pd.DataFrame, seconds_column: str, windows_hours: list[float]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = len(frame)

    for hours in windows_hours:
        seconds = hours * 3600
        matched = frame[seconds_column].notna() & (frame[seconds_column] <= seconds)
        matched_count = int(matched.sum())
        rows.append(
            {
                "window_hours": hours,
                "add_to_cart_events": total,
                "matched_purchases": matched_count,
                "conversion_rate": matched_count / total if total else 0.0,
            }
        )

    return rows


def analyze_windows(
    data_dir: Path,
    max_clients: int,
    seed: int,
    windows_hours: list[float],
) -> dict[str, Any]:
    sampled_clients = _load_client_sample(data_dir, max_clients=max_clients, seed=seed)
    client_set = set(int(client_id) for client_id in sampled_clients)

    add_to_cart = _load_events(data_dir, "add_to_cart.parquet", client_set)
    product_buy = _load_events(data_dir, "product_buy.parquet", client_set)

    same_sku = _next_purchase(add_to_cart, product_buy, ["client_id", "sku"], "same_sku")
    any_sku = _next_purchase(
        add_to_cart[["client_id", "timestamp", "sku"]],
        product_buy[["client_id", "timestamp", "sku"]],
        ["client_id"],
        "any_sku",
    )

    return {
        "dataset": {
            "path": str(data_dir),
            "sampled_clients": int(len(sampled_clients)),
            "add_to_cart_events": int(len(add_to_cart)),
            "product_buy_events": int(len(product_buy)),
            "unique_add_to_cart_clients": int(add_to_cart["client_id"].nunique()),
            "unique_product_buy_clients": int(product_buy["client_id"].nunique()),
        },
        "question": "After add_to_cart at time t, does the client buy soon after?",
        "same_sku": _window_summary(same_sku, "seconds_to_buy_same_sku", windows_hours),
        "any_sku": _window_summary(any_sku, "seconds_to_buy_any_sku", windows_hours),
        "evidence_level": "event-relative descriptive timing, not a causal estimate",
        "interpretation_note": (
            "This analysis tests short-term event timing. It is closer to the product question than the broad "
            "pre/post split, but it still needs controls or experimentation before causal interpretation."
        ),
    }


def _print_summary(result: dict[str, Any]) -> None:
    dataset = result["dataset"]
    print(
        f"sampled_clients={dataset['sampled_clients']} "
        f"add_to_cart_events={dataset['add_to_cart_events']} "
        f"product_buy_events={dataset['product_buy_events']}"
    )
    print()
    print("scope     window_hours  matched_purchases  conversion_rate")
    print("--------  ------------  -----------------  ---------------")
    for scope in ("same_sku", "any_sku"):
        for row in result[scope]:
            print(
                f"{scope.ljust(8)}  "
                f"{str(row['window_hours']).rjust(12)}  "
                f"{str(row['matched_purchases']).rjust(17)}  "
                f"{row['conversion_rate'] * 100:14.2f}%"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze event-relative add-to-cart purchase windows.")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data" / "archive")
    parser.add_argument("--max-clients", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--windows-hours", nargs="+", type=float, default=[1, 24, 168])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = analyze_windows(
        data_dir=args.data_dir,
        max_clients=args.max_clients,
        seed=args.seed,
        windows_hours=args.windows_hours,
    )

    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = REPO_ROOT / "experiments" / "runs" / f"event_windows_{args.max_clients}_{timestamp}.json"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, default=_json_default) + "\n", encoding="utf-8")
    _print_summary(result)
    print()
    print(f"Wrote result -> {args.output}")


if __name__ == "__main__":
    main()

