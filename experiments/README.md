# Experiments

Research prototypes, synthetic data, and notebooks.

Use this area to test causal modeling ideas before promoting them into `services/causal-engine`.

## Current Synerise Runs

`synerise_effects_5k.json` is the first simple run. It adjusts only by pre-period total activity.

`synerise_effects_5k_richer.json` is the stronger first-pass run. It adds:

- prior event counts
- prior purchase history
- recency of last pre-period event
- active-client membership
- SKU interaction count
- unique SKU count
- mean interacted product price
- mean category SKU count as a coarse popularity proxy
- overlap filtering for stratified estimates
- linear probability adjustment
- propensity-proxy stratification

The important early result:

```text
add_to_cart naive difference:             -9.07%
add_to_cart activity-adjusted difference: -2.44%
add_to_cart propensity-proxy difference:  +4.13%
add_to_cart regression-adjusted effect:   +1.94%
```

This does not prove add-to-cart causes later purchase. It shows the original negative result was not robust after stronger controls, which is exactly why the causal engine needs explicit assumptions and multiple adjustment views.
