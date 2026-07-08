# Dataset Strategy

## Current Dataset

Local path:

```text
data/archive/
```

Dataset:

RecSys25 Synerise Challenge

Available files:

- `page_visit.parquet`
- `search_query.parquet`
- `add_to_cart.parquet`
- `remove_from_cart.parquet`
- `product_buy.parquet`
- `product_properties.parquet`
- `input/relevant_clients.npy`
- `target/active_clients.npy`
- `target/propensity_category.npy`
- `target/propensity_sku.npy`
- `target/popularity_propensity_category.npy`
- `target/popularity_propensity_sku.npy`

## Is This a Good Starting Point?

Yes, but for a specific part of the system.

This dataset is useful for building the behavioral and causal inference layers:

- ordered user event streams
- product interaction journeys
- conversion-like outcomes such as purchase
- churn or activity targets
- propensity targets for products and categories
- product metadata for enrichment

It is less useful for validating the full DOM-tree hypothesis because it likely does not contain:

- DOM snapshots
- element hierarchy
- UI component structure
- button/form/modal identifiers
- page layout or copy context

So the dataset is good enough to start the causal engine, but not enough by itself to prove the DOM-as-product-graph thesis.

## How We Should Use It

Use Synerise as the first behavioral event benchmark.

Map events into a generic product journey:

```text
page_visit
  -> search_query
  -> add_to_cart
  -> remove_from_cart
  -> product_buy
```

Example causal questions:

- Does search behavior increase purchase probability?
- Does add-to-cart causally influence purchase, after adjusting for previous page visits and product/category popularity?
- Is remove-from-cart a negative causal signal or just a marker of higher shopping intent?
- Which event paths are most associated with active clients?
- Which categories or products have high propensity after specific event sequences?

## What We Need To Add

To test the core product thesis, pair this dataset with one of:

1. Synthetic DOM graphs

   Create fake product pages, category pages, carts, modals, and checkout steps. Attach Synerise-style events to synthetic DOM nodes.

2. Instrumented local demo site

   Build a small ecommerce demo, run our tracker on it, and collect real DOM snapshots plus events.

3. Hybrid mapping

   Treat product/category/page concepts from Synerise as coarse DOM/product nodes:

   - page visit as page node
   - product as product-card node
   - search query as search-input node
   - add-to-cart as CTA node
   - remove-from-cart as cart-control node
   - product buy as conversion outcome

This hybrid mapping is imperfect, but useful for early end-to-end prototypes.

## First Prototype Recommendation

Build the first prototype around a constrained ecommerce journey:

```text
visited product/category page
  -> searched
  -> added product to cart
  -> removed product from cart
  -> bought product
```

Initial treatment/outcome pairs:

- treatment: `search_query`, outcome: `product_buy`
- treatment: `add_to_cart`, outcome: `product_buy`
- treatment: `remove_from_cart`, outcome: `product_buy`

Initial confounders:

- prior page visit count
- prior search count
- product/category popularity
- client activity history
- recency of previous events

The first milestone should not be full causal discovery. It should be a transparent causal-analysis pipeline with explicit assumptions and simple effect estimates.

