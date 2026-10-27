# 03 · Semantic reranking

**Serves:** 2 · **Difficulty:** ★☆☆ · **Code:** `ingest/index_azure.py` (semantic config), `AzureStore.search`

## Method
1. Define a semantic configuration: title → `title`, content → `text`, keywords → `ingredients`.
2. Set `query_type="semantic"` and `semantic_configuration_name="recipes-semantic"`.
3. Use `@search.reranker_score` (0–4) as the relevance signal instead of raw RRF score.

## Taste test
As an experiment, compare top-3 for a vague query with and without semantic ranking. The current Azure implementation always enables semantic ranking; a toggle would need to be added for a controlled comparison. It does not currently enforce a reranker-score refusal threshold.

## Chef's notes
The vector query requests 50 nearest neighbors; Azure reranks the hybrid candidates, and Q&A requests four final sources by default. Larger candidate pools can help recall while keeping the generation prompt small, but the precision/cost trade-off needs measurement.
