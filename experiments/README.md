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

## Scaled Stability Check

The standard sweep writes timestamped outputs under `experiments/runs/`.

Latest checked run:

```text
synerise_overlap_5000_20260708_055716.json
synerise_overlap_50000_20260708_055716.json
synerise_overlap_100000_20260708_055716.json
```

Summary:

```text
treatment         clients  naive    activity  propensity  regression
search_query      5k       -1.66%   +2.29%    +3.56%      +5.14%
search_query      50k      -4.64%   +2.47%    +2.01%      +2.83%
search_query      100k     -4.70%   +2.07%    +1.84%      +2.43%

add_to_cart       5k       -9.07%   -2.44%    +4.13%      +1.94%
add_to_cart       50k      -10.53%  -1.14%    +2.26%      +2.81%
add_to_cart       100k     -10.64%  -1.15%    +1.99%      +2.19%

remove_from_cart  5k       -3.06%   +0.34%    +2.79%      +4.34%
remove_from_cart  50k      -5.20%   -0.56%    +2.80%      +3.35%
remove_from_cart  100k     -5.05%   +0.16%    +2.20%      +3.25%
```

This supports the current product story: raw descriptive differences can point in the wrong direction, while adjusted views recover a more stable relationship. The estimates are still adjusted associations, not final causal effects.

## Reproducible Runs

Run the standard sample-size sweep:

```bash
python experiments/scripts/run_synerise_experiments.py \
  --sample-sizes 5000 50000 100000
```

For a quick smoke test:

```bash
python experiments/scripts/run_synerise_experiments.py \
  --sample-sizes 1000 \
  --label smoke
```

Compare result files:

```bash
python experiments/scripts/compare_synerise_results.py \
  experiments/runs/*.json
```

The comparison table is the fastest way to see whether treatment directions remain stable as sample size increases.

The stratified estimators require overlap. A stratum is excluded if either treatment arm has fewer than 20 clients or fewer than 1% of the stratum.
