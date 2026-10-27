# 04 · Grounded answers, citations & "I don't know"

**Serves:** 2 · **Difficulty:** ★★☆ · **Code:** `src/ragcookbook/rag.py` (`ask`)

## Method
1. Tag every source `[r012]` in the prompt (`_format_sources`).
2. System prompt: answer **only** from sources, cite every claim, otherwise emit the exact refusal string.
3. Post-process: map recognized `[id]` tags back to `Citation(id, title, source, page)`; detect the exact refusal and return `grounded=False`. If no recognized tag is present, the current code falls back to the top source.
4. Pre-filter: refuse without generation when there are no hits. Local mode additionally applies a keyword-score threshold. Azure mode relies on the source-constrained prompt for relevance-based refusal; it does not apply the local threshold.

## Taste test
`python -m ragcookbook.cli ask "how do I make carbonara"` → cited. `ask "explain quantum chromodynamics"` → refusal. Both are asserted in `tests/test_core.py`.

## Chef's notes
Refusal is a feature: measure it (`refusal_rate_on_unanswerable`) alongside accuracy.

`grounded=True` is an application outcome flag, not proof that each generated claim is supported. Expected-source citation metrics do not replace claim-level groundedness evaluation, especially when citation fallback is enabled.
