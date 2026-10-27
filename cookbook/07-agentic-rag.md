# 07 · Agentic RAG

**Serves:** 2 · **Difficulty:** ★★★ · **Code:** `src/ragcookbook/agent.py`

## Method
1. Expose retrieval as **tools**: `search_recipes(query)` and `find_by_ingredients(ingredients, max_missing)`.
2. Loop: model → tool calls → results appended → model, up to `max_steps`.
3. Return the final answer plus the **tool trace** (shown in the UI) for transparency.

## Foundry Agent Service variant
The same two tool schemas can be registered as function tools on an agent created with `azure-ai-projects`
(`AIProjectClient.agents.create_agent(... tools=...)`); Foundry then manages threads, runs and tracing. The local loop
keeps the demo dependency-light and easy to unit test.

## Taste test
"Compare dinner options for chicken and carrots, and suggest a vegetarian side" → the agent should call both tools.

## Chef's notes
Agents cost more tokens and latency than a single RAG call. Use them for multi-step questions; keep simple questions on the fast path.
