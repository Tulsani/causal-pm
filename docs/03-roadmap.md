# Roadmap

## Phase 0: Project Definition

- Define the product thesis.
- Define canonical event and graph schemas.
- Choose first prototype question.
- Create synthetic data for a simple funnel.

## Phase 1: Local Prototype

Goal:

Build an end-to-end local demo that captures or loads events, builds a product graph, estimates a simple causal effect, and answers a PM question.

Scope:

- browser tracker stub
- local ingestion script
- JSONL or SQLite event store
- synthetic funnel data
- hand-constrained causal graph
- basic LLM-style query interpreter without external model dependency

Success criteria:

- user can ask "why did users drop after sign-up?"
- system identifies candidate causes
- system returns evidence and caveats
- graph output can be inspected

## Phase 2: Real Instrumentation

- Implement embeddable JavaScript tracker.
- Capture DOM element fingerprints.
- Capture event streams from a local demo website.
- Add privacy controls and input redaction.
- Add session reconstruction.

## Phase 3: Causal Engine

- Add graph construction from DOM and events.
- Add treatment/outcome declaration.
- Estimate causal effects with simple adjustment models.
- Add counterfactual query support.
- Track assumptions for each answer.

## Phase 4: LLM Interface

- Translate natural language questions into structured causal queries.
- Retrieve relevant graph and metric context.
- Call causal analysis tools.
- Generate concise explanations with uncertainty.

## Phase 5: Dashboard

- Visualize product graph and causal graph.
- Highlight drop-off nodes and high-effect paths.
- Let PMs select outcomes, segments, and interventions.

