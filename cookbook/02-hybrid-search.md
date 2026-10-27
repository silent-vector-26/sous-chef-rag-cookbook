# 02 · Hybrid search (BM25 + vectors)

**Serves:** 2 · **Difficulty:** ★★☆ · **Code:** `ingest/index_azure.py`, `store.AzureStore.search`

## Ingredients
- Azure AI Search (Basic) · `text-embedding-3-small` · Entra ID auth

## Method
1. Index fields: `title`, `text`, `ingredients[]`, `tags[]`, and `content_vector` (HNSW).
2. Embed `title + ingredients + method` at ingestion (`AzureStore.embed`).
3. Query with `search_text` **and** a `VectorizedQuery` in one request; Azure fuses the lists with Reciprocal Rank Fusion.

## Taste test
Ask "something cozy with root vegetables" (semantic) and "r012 carbonara" (exact keyword). Keyword-only misses the first; vector-only can blur the second. Hybrid handles both.

## Chef's notes
Keep an offline baseline (`LocalStore`) so you can quantify how much hybrid adds (recipe 08).
