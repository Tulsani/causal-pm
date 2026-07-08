from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _effect_by_treatment(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        effect["treatment"]: effect
        for effect in result.get("effects", [])
        if "treatment" in effect
    }


def _window_by_hours(rows: list[dict[str, Any]]) -> dict[float, dict[str, Any]]:
    return {float(row["window_hours"]): row for row in rows}


def build_graph(effect_result: dict[str, Any], event_window_result: dict[str, Any]) -> dict[str, Any]:
    effects = _effect_by_treatment(effect_result)
    same_sku_windows = _window_by_hours(event_window_result.get("same_sku", []))
    any_sku_windows = _window_by_hours(event_window_result.get("any_sku", []))
    same_sku_24h = same_sku_windows.get(24.0, {})
    any_sku_24h = any_sku_windows.get(24.0, {})

    nodes = [
        {
            "id": "page.product_detail",
            "kind": "page",
            "label": "Product detail page",
            "properties": {
                "source": "synthetic product-structure prior",
                "dataset_proxy": "page_visit",
            },
        },
        {
            "id": "element.search_input",
            "kind": "element",
            "label": "Search input",
            "properties": {
                "dataset_proxy": "search_query",
                "product_role": "intent formation",
            },
        },
        {
            "id": "element.product_card",
            "kind": "element",
            "label": "Product card",
            "properties": {
                "dataset_proxy": "page_visit + sku context",
                "product_role": "evaluation",
            },
        },
        {
            "id": "element.add_to_cart_button",
            "kind": "element",
            "label": "Add-to-cart button",
            "properties": {
                "dataset_proxy": "add_to_cart",
                "product_role": "late-funnel commitment",
            },
        },
        {
            "id": "element.remove_from_cart_button",
            "kind": "element",
            "label": "Remove-from-cart button",
            "properties": {
                "dataset_proxy": "remove_from_cart",
                "product_role": "cart editing or reconsideration",
            },
        },
        {
            "id": "action.search_query",
            "kind": "action",
            "label": "Search query",
            "properties": {
                "dataset_event": "search_query",
            },
        },
        {
            "id": "action.add_to_cart",
            "kind": "action",
            "label": "Add to cart",
            "properties": {
                "dataset_event": "add_to_cart",
            },
        },
        {
            "id": "action.remove_from_cart",
            "kind": "action",
            "label": "Remove from cart",
            "properties": {
                "dataset_event": "remove_from_cart",
            },
        },
        {
            "id": "outcome.product_buy",
            "kind": "outcome",
            "label": "Product purchase",
            "properties": {
                "dataset_event": "product_buy",
            },
        },
    ]

    edges: list[dict[str, Any]] = [
        {
            "source": "page.product_detail",
            "target": "element.search_input",
            "kind": "contains",
            "evidence": {"source": "synthetic DOM/product prior"},
        },
        {
            "source": "page.product_detail",
            "target": "element.product_card",
            "kind": "contains",
            "evidence": {"source": "synthetic DOM/product prior"},
        },
        {
            "source": "element.product_card",
            "target": "element.add_to_cart_button",
            "kind": "contains",
            "evidence": {"source": "synthetic DOM/product prior"},
        },
        {
            "source": "element.product_card",
            "target": "element.remove_from_cart_button",
            "kind": "contains",
            "evidence": {"source": "synthetic DOM/product prior"},
        },
        {
            "source": "element.search_input",
            "target": "action.search_query",
            "kind": "enables",
            "evidence": {"source": "event-to-product mapping"},
        },
        {
            "source": "element.add_to_cart_button",
            "target": "action.add_to_cart",
            "kind": "enables",
            "evidence": {"source": "event-to-product mapping"},
        },
        {
            "source": "element.remove_from_cart_button",
            "target": "action.remove_from_cart",
            "kind": "enables",
            "evidence": {"source": "event-to-product mapping"},
        },
        {
            "source": "action.search_query",
            "target": "action.add_to_cart",
            "kind": "precedes",
            "evidence": {
                "source": "product-journey prior",
                "interpretation": "search can precede product evaluation and carting",
            },
        },
        {
            "source": "action.add_to_cart",
            "target": "outcome.product_buy",
            "kind": "precedes",
            "weight": float(any_sku_24h.get("conversion_rate", 0.0)),
            "evidence": {
                "source": "event-relative timing",
                "window_hours": 24,
                "scope": "any_sku",
                "conversion_rate": any_sku_24h.get("conversion_rate"),
                "matched_purchases": any_sku_24h.get("matched_purchases"),
                "add_to_cart_events": any_sku_24h.get("add_to_cart_events"),
                "evidence_level": event_window_result.get("evidence_level"),
            },
        },
        {
            "source": "action.add_to_cart",
            "target": "outcome.product_buy",
            "kind": "influences",
            "weight": float(same_sku_24h.get("conversion_rate", 0.0)),
            "evidence": {
                "source": "event-relative timing",
                "window_hours": 24,
                "scope": "same_sku",
                "conversion_rate": same_sku_24h.get("conversion_rate"),
                "matched_purchases": same_sku_24h.get("matched_purchases"),
                "add_to_cart_events": same_sku_24h.get("add_to_cart_events"),
                "evidence_level": event_window_result.get("evidence_level"),
            },
        },
    ]

    for treatment, source in (
        ("search_query", "action.search_query"),
        ("add_to_cart", "action.add_to_cart"),
        ("remove_from_cart", "action.remove_from_cart"),
    ):
        effect = effects.get(treatment)
        if not effect:
            continue
        edges.append(
            {
                "source": source,
                "target": "outcome.product_buy",
                "kind": "causes_candidate",
                "weight": float(effect.get("regression_adjusted_risk_difference", 0.0)),
                "evidence": {
                    "source": "pre/post adjusted effect model",
                    "sampled_clients": effect_result.get("dataset", {}).get("sampled_clients"),
                    "naive_risk_difference": effect.get("naive_risk_difference"),
                    "activity_adjusted_risk_difference": effect.get("activity_adjusted_risk_difference"),
                    "propensity_proxy_adjusted_risk_difference": effect.get(
                        "propensity_proxy_adjusted_risk_difference"
                    ),
                    "regression_adjusted_risk_difference": effect.get(
                        "regression_adjusted_risk_difference"
                    ),
                    "regression_adjusted_approx_95_ci": effect.get(
                        "regression_adjusted_approx_95_ci"
                    ),
                    "evidence_level": effect.get("evidence_level"),
                },
            }
        )

    return {
        "graph_id": "synerise_product_journey_v0",
        "nodes": nodes,
        "edges": edges,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Causal PM graph from Synerise experiment outputs.")
    parser.add_argument("--effects", type=Path, required=True)
    parser.add_argument("--event-windows", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("experiments/graphs/synerise_product_journey_v0.json"))
    args = parser.parse_args()

    graph = build_graph(_load_json(args.effects), _load_json(args.event_windows))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote graph -> {args.output}")
    print(f"nodes={len(graph['nodes'])} edges={len(graph['edges'])}")


if __name__ == "__main__":
    main()

