# 02 · Hybrid search (BM25 + vectors)

**Serves:** 2 · **Difficulty:** ★★☆ · **Code:** `ingest/index_azure.py`, `store.AzureStore.search`

## Ingredients
- Azure AI Search (Free in this demo; subject to service quotas) · `text-embedding-3-small` · Entra ID auth

## Method
1. Index fields: `title`, `text`, `ingredients[]`, `tags[]`, and `content_vector` (HNSW).
2. Embed `title + ingredients + method` at ingestion (`AzureStore.embed`).
3. Query with `search_text` **and** a `VectorizedQuery` in one request; Azure fuses the lists with Reciprocal Rank Fusion.

## Taste test
Compare a broad query such as "something cozy with root vegetables" with a dish-name query such as "spaghetti carbonara." Inspect the retrieved IDs and scores. These illustrate different query styles; whether hybrid improves either case must be measured, not assumed.

## Chef's notes
Keep an offline baseline (`LocalStore`) so you can quantify how much hybrid adds (recipe 08).
