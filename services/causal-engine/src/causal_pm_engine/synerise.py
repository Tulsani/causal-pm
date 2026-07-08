from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


EVENT_FILES = {
    "page_visit": "page_visit.parquet",
    "search_query": "search_query.parquet",
    "add_to_cart": "add_to_cart.parquet",
    "remove_from_cart": "remove_from_cart.parquet",
    "product_buy": "product_buy.parquet",
}

TREATMENTS = ("search_query", "add_to_cart", "remove_from_cart")
SKU_EVENTS = ("add_to_cart", "remove_from_cart", "product_buy")
BASE_CONFOUNDERS = (
    "pre_page_visit_count",
    "pre_search_query_count",
    "pre_add_to_cart_count",
    "pre_remove_from_cart_count",
    "pre_product_buy_count",
    "pre_total_activity",
    "pre_any_product_buy",
    "days_since_last_pre_event",
    "is_active_client",
    "pre_sku_event_count",
    "pre_unique_sku_count",
    "pre_mean_price",
    "pre_mean_category_sku_count",
)


@dataclass(frozen=True)
class DatasetProfile:
    rows_by_event: dict[str, int]
    min_timestamp: str
    max_timestamp: str
    cutoff_timestamp: str


def _json_default(value: object) -> object:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _event_path(data_dir: Path, event_type: str) -> Path:
    return data_dir / EVENT_FILES[event_type]


def _timestamp_bounds(path: Path) -> tuple[pd.Timestamp, pd.Timestamp]:
    parquet = pq.ParquetFile(path)
    mins: list[pd.Timestamp] = []
    maxes: list[pd.Timestamp] = []

    schema_names = parquet.schema_arrow.names
    timestamp_idx = schema_names.index("timestamp")
    for i in range(parquet.metadata.num_row_groups):
        stats = parquet.metadata.row_group(i).column(timestamp_idx).statistics
        if stats and stats.min is not None and stats.max is not None:
            mins.append(pd.Timestamp(stats.min))
            maxes.append(pd.Timestamp(stats.max))

    if not mins or not maxes:
        timestamps = parquet.read(columns=["timestamp"]).to_pandas()["timestamp"]
        return pd.Timestamp(timestamps.min()), pd.Timestamp(timestamps.max())

    return min(mins), max(maxes)


def profile_dataset(data_dir: Path, train_fraction: float) -> DatasetProfile:
    rows_by_event: dict[str, int] = {}
    min_times: list[pd.Timestamp] = []
    max_times: list[pd.Timestamp] = []

    for event_type in EVENT_FILES:
        path = _event_path(data_dir, event_type)
        parquet = pq.ParquetFile(path)
        rows_by_event[event_type] = parquet.metadata.num_rows
        min_ts, max_ts = _timestamp_bounds(path)
        min_times.append(min_ts)
        max_times.append(max_ts)

    min_timestamp = min(min_times)
    max_timestamp = max(max_times)
    cutoff = min_timestamp + (max_timestamp - min_timestamp) * train_fraction

    return DatasetProfile(
        rows_by_event=rows_by_event,
        min_timestamp=min_timestamp.isoformat(),
        max_timestamp=max_timestamp.isoformat(),
        cutoff_timestamp=cutoff.isoformat(),
    )


def _load_client_sample(data_dir: Path, max_clients: int, seed: int) -> np.ndarray:
    relevant = np.load(data_dir / "input" / "relevant_clients.npy", allow_pickle=False)
    if max_clients >= len(relevant):
        return relevant

    rng = np.random.default_rng(seed)
    indices = rng.choice(len(relevant), size=max_clients, replace=False)
    return np.sort(relevant[indices])


def _load_active_clients(data_dir: Path) -> set[int]:
    active = np.load(data_dir / "target" / "active_clients.npy", allow_pickle=False)
    return set(int(client_id) for client_id in active)


def _load_product_properties(data_dir: Path) -> pd.DataFrame:
    properties = pd.read_parquet(data_dir / "product_properties.parquet")
    category_counts = properties.groupby("category").size().rename("category_sku_count")
    properties = properties.merge(category_counts, on="category", how="left")
    return properties[["sku", "category", "price", "category_sku_count"]]


def _add_counts(target: dict[int, int], counts: pd.Series) -> None:
    for client_id, count in counts.items():
        client_key = int(client_id)
        target[client_key] = target.get(client_key, 0) + int(count)


def _scan_event_features(
    data_dir: Path,
    event_type: str,
    client_ids: np.ndarray,
    cutoff: pd.Timestamp,
    product_properties: pd.DataFrame,
) -> dict[str, pd.Series]:
    path = _event_path(data_dir, event_type)
    parquet = pq.ParquetFile(path)
    client_set = set(int(client_id) for client_id in client_ids)

    before_counts: dict[int, int] = {}
    after_counts: dict[int, int] = {}
    pre_last_timestamp: dict[int, pd.Timestamp] = {}
    pre_url_uniques: list[pd.Series] = []
    pre_sku_frames: list[pd.DataFrame] = []

    columns = ["client_id", "timestamp"]
    schema_names = parquet.schema_arrow.names
    if "sku" in schema_names:
        columns.append("sku")
    if "url" in schema_names:
        columns.append("url")

    for row_group_idx in range(parquet.metadata.num_row_groups):
        table = parquet.read_row_group(row_group_idx, columns=columns)
        frame = table.to_pandas()
        frame = frame[frame["client_id"].isin(client_set)]
        if frame.empty:
            continue

        before = frame[frame["timestamp"] < cutoff]
        after = frame[frame["timestamp"] >= cutoff]

        _add_counts(before_counts, before.groupby("client_id").size())
        _add_counts(after_counts, after.groupby("client_id").size())

        if not before.empty:
            for client_id, timestamp in before.groupby("client_id")["timestamp"].max().items():
                client_key = int(client_id)
                previous = pre_last_timestamp.get(client_key)
                if previous is None or timestamp > previous:
                    pre_last_timestamp[client_key] = pd.Timestamp(timestamp)

        if "url" in before.columns and not before.empty:
            pre_url_uniques.append(before.groupby("client_id")["url"].nunique())

        if "sku" in before.columns and not before.empty:
            enriched = before[["client_id", "sku"]].merge(product_properties, on="sku", how="left")
            pre_sku_frames.append(enriched)

    features: dict[str, pd.Series] = {
        "before_count": pd.Series(before_counts, dtype="int64"),
        "after_count": pd.Series(after_counts, dtype="int64"),
        "pre_last_timestamp": pd.Series(pre_last_timestamp),
    }

    if pre_url_uniques:
        url_uniques = pd.concat(pre_url_uniques).groupby(level=0).sum()
        features["pre_unique_url_count"] = url_uniques.astype("int64")

    if pre_sku_frames:
        sku_frame = pd.concat(pre_sku_frames, ignore_index=True)
        grouped = sku_frame.groupby("client_id")
        features["pre_unique_sku_count"] = grouped["sku"].nunique().astype("int64")
        features["pre_mean_price"] = grouped["price"].mean()
        features["pre_mean_category_sku_count"] = grouped["category_sku_count"].mean()

    return features


def build_client_cohort(
    data_dir: Path,
    max_clients: int,
    train_fraction: float,
    seed: int,
) -> tuple[pd.DataFrame, DatasetProfile]:
    profile = profile_dataset(data_dir, train_fraction)
    cutoff = pd.Timestamp(profile.cutoff_timestamp)
    client_ids = _load_client_sample(data_dir, max_clients=max_clients, seed=seed)
    active_clients = _load_active_clients(data_dir)
    product_properties = _load_product_properties(data_dir)

    cohort = pd.DataFrame({"client_id": client_ids})
    cohort = cohort.set_index("client_id", drop=False)
    all_last_pre_timestamps: list[pd.Series] = []
    sku_feature_columns = ("pre_unique_sku_count", "pre_mean_price", "pre_mean_category_sku_count")

    for event_type in EVENT_FILES:
        features = _scan_event_features(
            data_dir,
            event_type,
            client_ids,
            cutoff,
            product_properties,
        )
        cohort[f"pre_{event_type}_count"] = features["before_count"]
        cohort[f"post_{event_type}_count"] = features["after_count"]

        if not features["pre_last_timestamp"].empty:
            all_last_pre_timestamps.append(features["pre_last_timestamp"])

        if event_type == "page_visit" and "pre_unique_url_count" in features:
            cohort["pre_unique_url_count"] = features["pre_unique_url_count"]

        if event_type in SKU_EVENTS:
            for column in sku_feature_columns:
                if column in features:
                    cohort[f"{event_type}_{column}"] = features[column]

    count_columns = [column for column in cohort.columns if column.endswith("_count")]
    cohort[count_columns] = cohort[count_columns].fillna(0).astype("int64")

    cohort["outcome_product_buy"] = cohort["post_product_buy_count"] > 0
    for treatment in TREATMENTS:
        cohort[f"treatment_{treatment}"] = cohort[f"pre_{treatment}_count"] > 0

    cohort["pre_total_activity"] = (
        cohort["pre_page_visit_count"]
        + cohort["pre_search_query_count"]
        + cohort["pre_add_to_cart_count"]
        + cohort["pre_remove_from_cart_count"]
        + cohort["pre_product_buy_count"]
    )
    cohort["pre_any_product_buy"] = cohort["pre_product_buy_count"] > 0
    cohort["is_active_client"] = cohort["client_id"].isin(active_clients)

    if all_last_pre_timestamps:
        last_pre_timestamp = pd.concat(all_last_pre_timestamps).groupby(level=0).max()
        cohort["last_pre_event_timestamp"] = last_pre_timestamp
        cohort["days_since_last_pre_event"] = (
            cutoff - cohort["last_pre_event_timestamp"]
        ).dt.total_seconds() / 86400
    else:
        cohort["days_since_last_pre_event"] = np.nan

    cohort["days_since_last_pre_event"] = cohort["days_since_last_pre_event"].fillna(
        (cutoff - pd.Timestamp(profile.min_timestamp)).total_seconds() / 86400
    )

    for base_column in sku_feature_columns:
        event_columns = [f"{event_type}_{base_column}" for event_type in SKU_EVENTS]
        existing_columns = [column for column in event_columns if column in cohort.columns]
        if not existing_columns:
            continue

        if base_column == "pre_unique_sku_count":
            cohort[base_column] = cohort[existing_columns].fillna(0).sum(axis=1)
        else:
            cohort[base_column] = cohort[existing_columns].mean(axis=1)

    cohort["pre_sku_event_count"] = (
        cohort["pre_add_to_cart_count"]
        + cohort["pre_remove_from_cart_count"]
        + cohort["pre_product_buy_count"]
    )

    confounder_columns = [
        "pre_unique_url_count",
        "pre_unique_sku_count",
        "pre_mean_price",
        "pre_mean_category_sku_count",
        "pre_sku_event_count",
    ]
    for column in confounder_columns:
        if column not in cohort.columns:
            cohort[column] = 0
    cohort[confounder_columns] = cohort[confounder_columns].fillna(0)

    return cohort.reset_index(drop=True), profile


def _risk(values: pd.Series) -> float:
    if len(values) == 0:
        return float("nan")
    return float(values.mean())


def _activity_strata(cohort: pd.DataFrame) -> pd.Series:
    activity = cohort["pre_total_activity"]
    ranked = activity.rank(method="first")
    unique_count = int(activity.nunique())
    if unique_count < 4:
        return pd.cut(ranked, bins=min(unique_count, 2), labels=False, duplicates="drop").fillna(0)
    return pd.qcut(ranked, q=4, labels=False, duplicates="drop").fillna(0)


def _numeric_matrix(cohort: pd.DataFrame, columns: Iterable[str]) -> tuple[np.ndarray, list[str]]:
    existing_columns = [column for column in columns if column in cohort.columns]
    matrix = cohort[existing_columns].copy()
    for column in existing_columns:
        if matrix[column].dtype == bool:
            matrix[column] = matrix[column].astype(float)
        else:
            matrix[column] = pd.to_numeric(matrix[column], errors="coerce")

    matrix = matrix.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return matrix.to_numpy(dtype=float), existing_columns


def _standardize(matrix: np.ndarray) -> np.ndarray:
    if matrix.size == 0:
        return matrix

    means = matrix.mean(axis=0)
    stds = matrix.std(axis=0)
    stds[stds == 0] = 1.0
    return (matrix - means) / stds


def _ols_treatment_effect(
    cohort: pd.DataFrame,
    treatment_column: str,
    confounders: Iterable[str],
) -> dict[str, object]:
    confounder_matrix, used_confounders = _numeric_matrix(cohort, confounders)
    treatment_vector = cohort[treatment_column].astype(float).to_numpy().reshape(-1, 1)
    outcome = cohort["outcome_product_buy"].astype(float).to_numpy()
    design = np.column_stack(
        [
            np.ones(len(cohort)),
            treatment_vector,
            _standardize(confounder_matrix),
        ]
    )
    coefficients, _, rank, _ = np.linalg.lstsq(design, outcome, rcond=None)
    fitted = design @ coefficients
    residuals = outcome - fitted
    degrees = max(len(outcome) - rank, 1)
    sigma2 = float((residuals @ residuals) / degrees)
    covariance = sigma2 * np.linalg.pinv(design.T @ design)
    std_error = float(np.sqrt(max(covariance[1, 1], 0.0)))
    coefficient = float(coefficients[1])

    return {
        "risk_difference": coefficient,
        "standard_error": std_error,
        "approx_95_ci": [coefficient - 1.96 * std_error, coefficient + 1.96 * std_error],
        "confounders": used_confounders,
        "method": "linear probability model with standardized confounders",
    }


def _propensity_proxy_strata(
    cohort: pd.DataFrame,
    treatment_column: str,
    confounders: Iterable[str],
) -> tuple[pd.Series, list[str]]:
    confounder_matrix, used_confounders = _numeric_matrix(cohort, confounders)
    treatment = cohort[treatment_column].astype(float).to_numpy()

    if confounder_matrix.size == 0 or len(np.unique(treatment)) < 2:
        score = cohort["pre_total_activity"].rank(method="first")
        return pd.qcut(score, q=4, labels=False, duplicates="drop").fillna(0), used_confounders

    design = np.column_stack([np.ones(len(cohort)), _standardize(confounder_matrix)])
    coefficients, *_ = np.linalg.lstsq(design, treatment, rcond=None)
    propensity_proxy = design @ coefficients
    ranked = pd.Series(propensity_proxy, index=cohort.index).rank(method="first")
    return pd.qcut(ranked, q=5, labels=False, duplicates="drop").fillna(0), used_confounders


def _confounders_for_treatment(treatment: str) -> tuple[str, ...]:
    treatment_count_column = f"pre_{treatment}_count"
    return tuple(
        column for column in BASE_CONFOUNDERS
        if column != treatment_count_column
    )


def _stratified_effect(
    cohort: pd.DataFrame,
    treatment_column: str,
    stratum_column: str,
    min_arm_size: int = 20,
    min_arm_fraction: float = 0.01,
) -> dict[str, object]:
    adjusted_effect = 0.0
    adjusted_weight = 0.0
    strata: list[dict[str, object]] = []
    dropped_strata: list[dict[str, object]] = []

    for stratum, group in cohort.groupby(stratum_column):
        group_treated = group[group[treatment_column]]
        group_control = group[~group[treatment_column]]
        required_arm_size = max(min_arm_size, int(len(group) * min_arm_fraction))
        if len(group_treated) < required_arm_size or len(group_control) < required_arm_size:
            dropped_strata.append(
                {
                    "stratum": int(stratum),
                    "clients": int(len(group)),
                    "treated_clients": int(len(group_treated)),
                    "control_clients": int(len(group_control)),
                    "reason": f"fewer than {required_arm_size} clients in one arm",
                }
            )
            continue

        stratum_treated_risk = _risk(group_treated["outcome_product_buy"])
        stratum_control_risk = _risk(group_control["outcome_product_buy"])
        stratum_effect = stratum_treated_risk - stratum_control_risk
        weight = len(group) / len(cohort)
        adjusted_effect += stratum_effect * weight
        adjusted_weight += weight
        strata.append(
            {
                "stratum": int(stratum),
                "clients": int(len(group)),
                "treated_clients": int(len(group_treated)),
                "control_clients": int(len(group_control)),
                "treated_risk": stratum_treated_risk,
                "control_risk": stratum_control_risk,
                "risk_difference": stratum_effect,
                "weight": weight,
            }
        )

    if adjusted_weight:
        effect = adjusted_effect / adjusted_weight
    else:
        effect = float("nan")

    return {
        "risk_difference": effect,
        "strata": strata,
        "dropped_strata": dropped_strata,
        "included_weight": adjusted_weight,
        "min_arm_size": min_arm_size,
        "min_arm_fraction": min_arm_fraction,
    }


def estimate_effect(cohort: pd.DataFrame, treatment: str) -> dict[str, object]:
    treatment_column = f"treatment_{treatment}"
    if treatment_column not in cohort.columns:
        raise ValueError(f"Unknown treatment: {treatment}")

    treated = cohort[cohort[treatment_column]]
    control = cohort[~cohort[treatment_column]]

    treated_risk = _risk(treated["outcome_product_buy"])
    control_risk = _risk(control["outcome_product_buy"])

    cohort = cohort.copy()
    treatment_confounders = _confounders_for_treatment(treatment)
    cohort["activity_stratum"] = _activity_strata(cohort)
    activity_adjustment = _stratified_effect(
        cohort,
        treatment_column,
        "activity_stratum",
    )
    cohort["propensity_proxy_stratum"], propensity_confounders = _propensity_proxy_strata(
        cohort,
        treatment_column,
        treatment_confounders,
    )
    propensity_adjustment = _stratified_effect(
        cohort,
        treatment_column,
        "propensity_proxy_stratum",
    )
    regression_adjusted = _ols_treatment_effect(cohort, treatment_column, treatment_confounders)

    return {
        "treatment": treatment,
        "outcome": "post_period_product_buy",
        "clients": int(len(cohort)),
        "treated_clients": int(len(treated)),
        "control_clients": int(len(control)),
        "treated_risk": treated_risk,
        "control_risk": control_risk,
        "naive_risk_difference": treated_risk - control_risk,
        "activity_adjusted_risk_difference": activity_adjustment["risk_difference"],
        "propensity_proxy_adjusted_risk_difference": propensity_adjustment["risk_difference"],
        "regression_adjusted_risk_difference": regression_adjusted["risk_difference"],
        "regression_adjusted_standard_error": regression_adjusted["standard_error"],
        "regression_adjusted_approx_95_ci": regression_adjusted["approx_95_ci"],
        "adjustment": "activity strata, propensity-proxy strata, and linear probability adjustment",
        "confounders": regression_adjusted["confounders"],
        "propensity_proxy_confounders": propensity_confounders,
        "evidence_level": "adjusted association, not a causal estimate unless ignorability assumptions hold",
        "activity_strata": activity_adjustment["strata"],
        "activity_dropped_strata": activity_adjustment["dropped_strata"],
        "activity_included_weight": activity_adjustment["included_weight"],
        "propensity_proxy_strata": propensity_adjustment["strata"],
        "propensity_proxy_dropped_strata": propensity_adjustment["dropped_strata"],
        "propensity_proxy_included_weight": propensity_adjustment["included_weight"],
        "assumptions": [
            "observed pre-period activity, recency, lifecycle, and product-property features capture major baseline intent differences",
            "post-period product_buy is a valid conversion outcome",
            "no major unobserved confounder remains after adjustment",
            "treatment occurs before the outcome because of the time split",
            "active client membership is treated as a lifecycle proxy and may leak future activity depending on target construction",
        ],
    }


def run_analysis(
    data_dir: Path,
    max_clients: int,
    train_fraction: float,
    seed: int,
    treatments: Iterable[str],
) -> dict[str, object]:
    cohort, profile = build_client_cohort(
        data_dir=data_dir,
        max_clients=max_clients,
        train_fraction=train_fraction,
        seed=seed,
    )
    return {
        "dataset": {
            "path": str(data_dir),
            "profile": profile.__dict__,
            "sampled_clients": int(len(cohort)),
            "clients_with_post_purchase": int(cohort["outcome_product_buy"].sum()),
            "feature_columns": [column for column in BASE_CONFOUNDERS if column in cohort.columns],
        },
        "effects": [estimate_effect(cohort, treatment) for treatment in treatments],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a first-pass Synerise causal analysis.")
    parser.add_argument("--data-dir", type=Path, default=Path("data/archive"))
    parser.add_argument("--max-clients", type=int, default=10_000)
    parser.add_argument("--train-fraction", type=float, default=0.7)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--treatment", choices=TREATMENTS, action="append")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    treatments = args.treatment or list(TREATMENTS)
    result = run_analysis(
        data_dir=args.data_dir,
        max_clients=args.max_clients,
        train_fraction=args.train_fraction,
        seed=args.seed,
        treatments=treatments,
    )
    payload = json.dumps(result, indent=2, default=_json_default)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
