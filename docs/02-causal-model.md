# Causal Model

## Modeling Principle

The DOM tree provides structure. Event data provides evidence. Causal assumptions provide meaning.

None of these are sufficient alone.

## Graph Layers

### 1. Product Structure Graph

Derived from DOM snapshots and route/component metadata.

Example edges:

- page contains form
- form contains input
- form contains submit button
- modal overlays checkout page

This graph describes what the user could interact with.

### 2. Behavioral Sequence Graph

Derived from observed event streams.

Example edges:

- viewed pricing -> clicked CTA
- clicked CTA -> opened sign-up modal
- typed email -> submitted form
- opened modal -> bounced

This graph describes what users actually did.

### 3. Causal Candidate Graph

Combines product structure, event sequence, outcomes, and assumptions.

Example claims:

- opening the modal may affect sign-up completion
- form length may affect submission probability
- viewing pricing before sign-up may affect conversion intent

This graph describes what may causally influence outcomes.

## Query Shape

A PM question should be normalized into:

```json
{
  "question": "What if we removed the interstitial modal?",
  "treatment": "modal.opened",
  "intervention": "do(modal.opened = false)",
  "outcome": "signup.completed",
  "population": "new visitors",
  "time_window": "last_30_days"
}
```

## Evidence Levels

The system should distinguish between:

- descriptive pattern: users who saw X converted less
- adjusted association: users who saw X converted less after controlling for Y
- causal estimate: under stated assumptions, X reduced conversion by Z
- experimental result: randomized evidence supports X causing Y

## Early Prototype Approach

Start with constrained, explicit assumptions:

- one site
- one funnel
- one conversion outcome
- DOM snapshots plus event streams
- manually declared candidate treatments
- simple effect estimation before full causal discovery

This keeps the prototype honest while making the causal workflow tangible.

