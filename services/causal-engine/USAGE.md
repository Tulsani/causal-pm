# Causal Engine Usage

Run the first Synerise prototype from the repository root with the conda Python:

```bash
/Users/tulsani/miniconda3/bin/python services/causal-engine/src/causal_pm_engine/synerise.py \
  --data-dir data/archive \
  --max-clients 10000 \
  --output experiments/synerise_effects.json
```

Then explain the result locally:

```bash
/Users/tulsani/miniconda3/bin/python services/llm-interface/src/causal_pm_llm/explain.py \
  --result experiments/synerise_effects.json \
  --question "Which pre-period behavior appears most influential for later purchase?"
```

If `OPENAI_API_KEY` is set, call the LLM interface with:

```bash
/Users/tulsani/miniconda3/bin/python services/llm-interface/src/causal_pm_llm/explain.py \
  --result experiments/synerise_effects.json \
  --question "Which pre-period behavior appears most influential for later purchase?" \
  --use-openai
```

## Current Estimator

The current estimator is intentionally simple:

- split the event history by time
- use pre-cutoff events as treatments and confounders
- use post-cutoff `product_buy` as conversion outcome
- estimate naive risk difference
- estimate an activity-adjusted risk difference by stratifying clients by pre-period total activity
- estimate a propensity-proxy adjusted risk difference with overlap filtering
- estimate a regression-adjusted risk difference with a dependency-free linear probability model

Current confounders include:

- prior event counts
- prior purchase history
- recency of last pre-period event
- active-client membership
- SKU interaction count
- unique SKU count
- mean interacted product price
- mean category SKU count as a coarse popularity proxy

This is not yet full causal discovery. It is the first working slice of the causal analysis pipeline.
