# 04 · Grounded answers, citations & "I don't know"

**Serves:** 2 · **Difficulty:** ★★☆ · **Code:** `src/ragcookbook/rag.py` (`ask`)

## Method
1. Tag every source `[r012]` in the prompt (`_format_sources`).
2. System prompt: answer **only** from sources, cite every claim, otherwise emit the exact refusal string.
3. Post-process: map `[id]` tags back to `Citation(id, title, source, page)`; detect the refusal and return `grounded=False`.
4. Pre-filter: if retrieval returns nothing above threshold, refuse **without** calling the LLM (cheaper, safer).

## Taste test
`python -m ragcookbook.cli ask "how do I make carbonara"` → cited. `ask "explain quantum chromodynamics"` → refusal. Both are asserted in `tests/test_core.py`.

## Chef's notes
Refusal is a feature: measure it (`refusal_rate_on_unanswerable`) alongside accuracy.
