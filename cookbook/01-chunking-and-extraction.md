# 01 · Chunking & structured extraction

**Serves:** 1–2 · **Difficulty:** ★☆☆ · **Code:** `src/ragcookbook/extract.py`, `ingest/build_dataset.py`

## Ingredients
- Raw recipe text with ingredient lines (`2 tbsp olive oil, divided`)
- Optional: Azure OpenAI for structured extraction

## Method
1. **Chunk by meaning, not by size.** A recipe is the natural unit: one document per recipe keeps ingredients and method together, so a retrieved chunk is always answerable.
2. **Extract canonical ingredients.** `extract_all` strips quantities, units and prep words, then `normalize` folds plurals/synonyms (`scallions → green onion`, `olive oil → oil`).
3. For messy text, switch to `python -m ingest.build_dataset --llm` (JSON-mode extraction).
4. Store both `ingredient_lines` (for display) and `ingredients` (for filtering/ranking).

## Taste test
`python -m ingest.build_dataset` then inspect `data/recipes.json`. Compare heuristic vs LLM output on your own recipes.

## Chef's notes
Fixed 512-token chunks would split ingredient lists from methods and hurt both retrieval and ingredient matching. Evaluate chunking choices in recipe 08.
