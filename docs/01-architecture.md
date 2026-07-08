# Architecture

## Pipeline

```text
Client Website
  -> Browser Tracker
  -> Event Ingestion API
  -> Session/Event Store
  -> DOM Graph Extractor
  -> Causal Graph Builder
  -> Causal Analysis Engine
  -> LLM Query Interface
  -> Dashboard
```

## 1. Browser Tracker

Captures product structure and user behavior from customer websites.

Responsibilities:

- assign anonymous visitor and session IDs
- capture page views and route changes
- capture clicks, form interactions, scroll depth, hovers, submits, and timing events
- capture DOM context for interacted elements
- generate stable element fingerprints
- batch and send events to ingestion

Important design constraint:

The tracker should capture enough context for causal modeling without collecting sensitive user input by default.

## 2. Event Ingestion

Receives browser events and normalizes them.

Responsibilities:

- validate event payloads
- enrich events with server timestamps and request metadata
- redact or reject sensitive fields
- write ordered events into storage
- expose session replay style retrieval for downstream services

## 3. Session Store

Stores ordered event streams.

Early prototype options:

- local JSONL files
- SQLite
- Postgres

Later production options:

- Kafka or Redpanda for streaming
- Postgres or ClickHouse for analytics
- object storage for raw events

## 4. DOM/Product Graph Store

Stores graph representations of pages and flows.

Graph nodes may include:

- page
- route
- DOM element
- component
- action
- user state
- outcome

Graph edges may include:

- parent-child DOM containment
- visual or semantic proximity
- event sequence transition
- action enables next state
- action associated with outcome

## 5. Causal Engine

Turns product graphs and event data into causal models.

Responsibilities:

- construct candidate DAGs
- apply product-structure priors from DOM hierarchy
- estimate treatment effects for product actions
- run counterfactual queries
- expose confidence and assumptions

Candidate methods:

- constraint-based discovery such as PC
- score-based discovery such as GES
- differentiable DAG learning such as NOTEARS
- uplift or treatment-effect models for specific interventions
- manually constrained graphs for early prototypes

## 6. LLM Interface

Translates PM questions into structured causal analysis tasks.

Responsibilities:

- parse natural language questions
- identify outcome, treatment, segment, and time window
- call causal tools
- explain results in PM-friendly language
- refuse overconfident causal claims when evidence is weak

## 7. Dashboard

Shows:

- causal product graph
- high-impact paths
- drop-off nodes
- counterfactual scenarios
- natural language analysis

