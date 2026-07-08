# Causal PM

Causal PM is a research-to-product project for causal product analytics.

The core idea is that product interfaces already encode a directed structure: users encounter pages, DOM nodes, copy, forms, modals, and calls to action in constrained orders. That DOM and interaction structure can be used as a causal prior, then updated with observed behavioral data to help PMs ask and answer causal questions about user journeys.

## Working Hypothesis

Traditional analytics tools are mostly descriptive:

- what users clicked
- where users dropped off
- which funnels performed better
- what correlated with conversion

Causal PM aims to move from descriptive analytics to causal product reasoning:

- which interface element plausibly caused drop-off
- which action has the largest effect on conversion
- what would happen if a modal, step, field, or CTA changed
- which paths are structurally necessary versus merely common

The DOM tree is not treated as truth by itself. It is treated as a product-structure graph that becomes useful when combined with event streams, outcomes, experiments, and causal assumptions.

## System Shape

```text
Browser Tracker
  -> Event Ingestion
  -> Session Store
  -> DOM/Product Graph Store
  -> Causal Engine
  -> LLM Query Interface
  -> PM Dashboard
```

## Repository Structure

```text
apps/
  dashboard/             PM-facing UI for querying and visualizing causal graphs

docs/
  00-product-thesis.md   Core thesis and product framing
  01-architecture.md     End-to-end system architecture
  02-causal-model.md     Causal graph assumptions and modeling approach
  03-roadmap.md          Build plan and milestones
  04-dataset-strategy.md How local datasets fit the first prototype

experiments/             Research notebooks, prototypes, and synthetic tests

infra/                   Deployment and local infrastructure config

packages/
  tracker/               Browser-side DOM and interaction capture script

schemas/
  event.schema.json      Canonical event payload shape
  graph.schema.json      Canonical causal/product graph shape

services/
  ingestion/             API/service that receives and normalizes events
  causal-engine/         Graph construction, causal inference, counterfactuals
  llm-interface/         Natural language to causal-query layer
```

## First Build Target

The first useful prototype should answer one constrained question:

> Given a captured DOM snapshot, a sequence of user events, and a conversion outcome, can we produce a causal product graph that lets a PM ask why users drop off at a specific point?

That prototype should use synthetic or local data before trying to become a production analytics platform.
