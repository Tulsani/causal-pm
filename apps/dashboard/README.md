# Dashboard

PM-facing interface for exploring causal product analytics.

Initial views:

- journey graph
- causal graph
- drop-off analysis
- intervention query panel
- natural language answer panel

The first dashboard can be static or local-only. The important thing is to make the causal workflow inspectable.

## V1 Static Dashboard

Run from the repository root:

```bash
python -m http.server 8080
```

Open:

```text
http://localhost:8080/apps/dashboard/src/
```

The dashboard loads:

- `experiments/graphs/synerise_product_journey_v0.json`
- `experiments/runs/synerise_overlap_100000_20260708_055716.json`
- `experiments/runs/event_windows_100000_20260708.json`

V1 views:

- Ask: deterministic PM-facing inference over current causal outputs
- Evidence: raw vs adjusted treatment table and event-window rates
- Graph: product journey graph with structural and evidence edges
- Next Tests: suggested follow-up analyses
