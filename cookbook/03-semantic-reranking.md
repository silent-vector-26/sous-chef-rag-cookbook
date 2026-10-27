# 03 · Semantic reranking

**Serves:** 2 · **Difficulty:** ★☆☆ · **Code:** `ingest/index_azure.py` (semantic config), `AzureStore.search`

## Method
1. Define a semantic configuration: title → `title`, content → `text`, keywords → `ingredients`.
2. Set `query_type="semantic"` and `semantic_configuration_name="recipes-semantic"`.
3. Use `@search.reranker_score` (0–4) as the relevance signal instead of raw RRF score.

## Taste test
Compare top-3 for a vague query with and without semantic ranking. Reranker scores are also a better refusal threshold than BM25 scores.

## Chef's notes
Retrieve wide (top 50), rerank, then send only top 3–5 to the LLM: better precision, lower token cost.
