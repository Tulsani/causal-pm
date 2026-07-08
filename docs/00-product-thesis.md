# Product Thesis

## One-Line Idea

Causal PM is a causal analytics platform that uses DOM structure and user interaction data to help product managers reason about why users behave the way they do, not just what they did.

## Core Claim

Product analytics currently gives PMs event counts, funnels, cohorts, and correlations. PMs then perform informal causal reasoning in their heads:

- "Users are dropping after sign-up because the onboarding form is too long."
- "The pricing page CTA is probably more important than the homepage hero."
- "The interstitial modal might be hurting conversion."

Causal PM makes that causal reasoning explicit.

## DOM Tree as a Causal Prior

The DOM tree is not automatically a causal graph. A button does not cause a click just because it exists in the DOM.

But the DOM tree is a useful causal prior because it captures product structure:

- visual and semantic hierarchy
- parent-child relationships between UI elements
- available user actions
- page-level context
- ordering constraints imposed by the interface
- relationships between copy, controls, forms, and outcomes

When joined with behavioral event data, that structure can seed a causal graph over product interactions.

## Product Promise

A PM should be able to ask:

- Why are users dropping off after sign-up?
- Which UI element most influences conversion?
- What would happen if we removed this modal?
- Which step in onboarding has the largest negative causal effect?
- Are users bouncing because of pricing, copy, latency, form complexity, or navigation?

The system should respond with:

- a causal explanation
- supporting evidence
- uncertainty or confidence
- suggested follow-up analyses
- a visual graph of the relevant journey

## Wedge

Start with web products and browser instrumentation.

The initial product does not need to solve all causal inference. It needs to provide a credible workflow for one high-value PM question:

> What caused users to drop before conversion in this journey?

