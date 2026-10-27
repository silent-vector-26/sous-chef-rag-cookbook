# 05 · Ingredient search: filters + domain-aware ranking

**Serves:** the headline feature · **Difficulty:** ★★★ · **Code:** `ingredient_search.py`, `rag.cook_with`, `store.candidates_by_ingredients`

> "I have chicken, potatoes and carrots" → recipes ranked by the **fewest ingredients you still need to buy**.

## Method
1. **Parse** the message into a pantry (`llm.parse_pantry` — JSON-mode LLM; `parse_pantry_heuristic` offline).
2. **Normalize** to the same canonical vocabulary as the index (plural/synonym folding).
3. **Retrieve candidates** with an OData filter on the `ingredients` collection:
   `ingredients/any(i: search.in(i, 'chicken,potato,carrot', ','))` — wide recall, cheap.
4. **Re-rank in code** (not by an LLM — it is deterministic and testable):
   `missing = recipe − pantry − staples`; sort by `(len(missing), -len(have), -retrieval_score, title)`.
5. **Explain**: owned vs missing, a combined shopping list, and `unlock_suggestions` — the one purchase that completes the most recipes.

## Taste test
```
python -m ragcookbook.cli cook "I have chicken, potatoes and carrots" --max-missing 2
python -m ragcookbook.cli cook "I have eggs, potato, onion" --diet vegetarian
```

## Chef's notes
Use the LLM for fuzzy language (parsing) and plain code for exact logic (set arithmetic). Staples (salt, pepper, water, oil) are excluded or every recipe looks "missing" something. Results are ordered within the retrieved candidate pool, not over an exhaustive global recipe catalog.
