# Tracker Package

Embeddable browser script for collecting DOM context and user interaction events.

Initial responsibilities:

- create anonymous visitor and session IDs
- listen for page views, clicks, form events, scrolls, and route changes
- compute stable element fingerprints
- capture safe DOM context
- batch events to the ingestion service

Privacy defaults:

- do not collect raw input values
- redact password, email, phone, payment, and hidden fields
- allow customer-side deny lists for selectors and attributes

