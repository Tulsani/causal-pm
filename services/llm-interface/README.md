# LLM Interface

Natural language interface for causal product questions.

Initial responsibilities:

- parse PM questions into structured causal queries
- identify treatment, outcome, segment, and time window
- call causal-engine tools
- return concise explanations with evidence level and uncertainty

The interface should avoid causal overclaiming. If the graph or data only supports association, the response should say so.

