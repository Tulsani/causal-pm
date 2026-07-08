from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


SYSTEM_PROMPT = """You explain causal product analytics results to product managers.
Be concise. Distinguish correlation, adjusted association, and causal evidence.
Mention assumptions and uncertainty instead of overclaiming."""


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def _format_interval(values: list[float]) -> str:
    return f"[{_format_percent(values[0])}, {_format_percent(values[1])}]"


def deterministic_explanation(result: dict[str, object], question: str) -> str:
    effects = result.get("effects", [])
    if not effects:
        return "No effects were available to explain."

    lines = [f"Question: {question}", ""]
    lines.append("Short answer: this run supports an adjusted-association read, not a final causal claim.")
    lines.append("")

    for effect in effects:
        treatment = effect["treatment"]
        lines.append(f"For `{treatment}`:")
        lines.append(
            f"- Treated conversion risk: {_format_percent(effect['treated_risk'])}; "
            f"control risk: {_format_percent(effect['control_risk'])}."
        )
        lines.append(
            f"- Naive difference: {_format_percent(effect['naive_risk_difference'])}; "
            f"activity-adjusted difference: {_format_percent(effect['activity_adjusted_risk_difference'])}."
        )
        if "propensity_proxy_adjusted_risk_difference" in effect:
            lines.append(
                "- Propensity-proxy adjusted difference: "
                f"{_format_percent(effect['propensity_proxy_adjusted_risk_difference'])}."
            )
        if "regression_adjusted_risk_difference" in effect:
            lines.append(
                "- Regression-adjusted difference: "
                f"{_format_percent(effect['regression_adjusted_risk_difference'])} "
                f"with approximate 95% CI {_format_interval(effect['regression_adjusted_approx_95_ci'])}."
            )
        lines.append(f"- Evidence level: {effect['evidence_level']}.")
        lines.append("")

    lines.append("Interpretation: compare the adjusted estimates. If a treatment remains large and directionally stable across adjustment methods, it is a better candidate for deeper causal modeling or an experiment.")
    return "\n".join(lines)


def openai_explanation(result: dict[str, object], question: str, model: str) -> str:
    from openai import OpenAI

    client = OpenAI()
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    "Causal analysis JSON:\n"
                    f"{json.dumps(result, indent=2)[:18000]}"
                ),
            },
        ],
    )
    return response.output_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Explain a causal-engine result.")
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--use-openai", action="store_true")
    parser.add_argument("--model", default="gpt-4.1-mini")
    args = parser.parse_args()

    result = json.loads(args.result.read_text(encoding="utf-8"))
    if args.use_openai:
        if not os.environ.get("OPENAI_API_KEY"):
            raise SystemExit("OPENAI_API_KEY is required for --use-openai")
        print(openai_explanation(result, args.question, args.model))
    else:
        print(deterministic_explanation(result, args.question))


if __name__ == "__main__":
    main()
