# 07 · Agentic RAG

**Serves:** 2 · **Difficulty:** ★★★ · **Code:** `src/ragcookbook/agent.py`

## Method
1. Expose retrieval as **tools**: `search_recipes(query)` and `find_by_ingredients(ingredients, max_missing)`.
2. Loop: model → tool calls → results appended → model, up to `max_steps`.
3. Return the final answer plus the **tool trace** (shown in the UI) for transparency.

## Foundry Agent Service variant
The same tool concepts could be adapted to a hosted Foundry agent. This repository implements the direct Azure OpenAI tool loop, not a Foundry-hosted agent. SDK APIs and hosted-agent setup vary by version; treat this as an extension idea, not a runnable integration supplied by the demo.

## Taste test
"Compare dinner options for chicken and carrots, and suggest a vegetarian side" → inspect which retrieval tools the model chooses and whether the answer cites recipe IDs. Tool selection is model-dependent; both tools are available, but a specific call sequence is not guaranteed.

## Chef's notes
Agents cost more tokens and latency than a single RAG call. Use them for multi-step questions; keep simple questions on the fast path.

The dietary widgets are not forwarded into the agent loop, and its top-level prompt/direct search tool do not share the Q&A safety gate. The displayed trace contains tool names and arguments, not private model reasoning. See [safety](09-safety.md) for the current guardrail scope.
