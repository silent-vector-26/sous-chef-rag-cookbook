# Building Sous-chef: a recipe RAG that ranks by what you're missing

*Draft write-up for a blog post or LinkedIn article. Repo: https://github.com/silent-vector-26/sous-chef-rag-cookbook*

## The problem

"What can I cook with chicken, potatoes and carrots?" is not a similarity-search problem. The best answer is the recipe where you are missing the *fewest* ingredients, and a pure vector search happily returns a beautiful recipe that needs eleven things you don't have. Classic RAG also tends to answer confidently when the corpus has nothing relevant. I wanted a demo that gets both right and that I can run for about $5 a month.

## Architecture

- **Retrieval:** Azure AI Search with hybrid search (BM25 + 1536-d vectors from `text-embedding-3-small`) and the semantic ranker. Auth is Entra ID only, with no keys anywhere.
- **Generation:** Azure OpenAI (`gpt-5.4-mini`) with a grounded prompt: answer only from sources, cite `[r001]`-style ids, otherwise refuse.
- **Ingredient search:** the LLM parses "I have chicken, potatoes and 2 carrots" into canonical ingredients. Candidates come from a filtered Search query, and ranking happens in plain code: `(missing count, -have count, -retrieval score, title)`. Staples such as salt, pepper, water and oil are never counted as missing. The same pool also drives a shopping list and "buy X to unlock N more recipes" tips.
- **Agentic mode:** the model calls `search_recipes` and `find_by_ingredients` tools, possibly several times, to compare dishes.
- **Multimodal:** a fridge photo is turned into ingredients with a vision-capable chat call.
- **Safety:** Azure AI Content Safety (Prompt Shields plus harm categories) before retrieval, and a system prompt that ignores instructions embedded in sources.
- **Ops:** Bicep + `azd`, a Container App that scales to zero, GitHub Actions CI and OIDC-based CD on merge, OpenTelemetry to Application Insights, and a budget alert.

## Design choices worth defending

1. **Deterministic ranking beats asking an LLM to rank.** The LLM only does language understanding (parsing the pantry). The ordering is testable code with unit tests.
2. **Refusal is a feature.** The golden set includes out-of-scope questions and prompt-injection attempts; the Azure run refuses all 7 of them.
3. **Least privilege.** The running app holds only Search Index Data Reader. The CI identity is Contributor plus an RBAC Administrator limited by an ABAC condition to six role definitions.
4. **Cost is a design input.** Search runs on the Free tier and the app scales to zero, which is about $5/month at idle. The SDD records the production alternative (Basic Search, `minReplicas: 1`).

## Evaluation

A 25-case golden set over a 205-recipe synthetic corpus (180 LLM-generated, so the numbers are optimistic):

| metric | Azure (hybrid + semantic) |
|---|---|
| retrieval recall@5 / MRR | 1.00 / 1.00 |
| refusal on unanswerable and injection | 1.00 |
| pantry top-1 / sorted by missing | 1.00 / 1.00 |
| citation accuracy | 0.92 (varies by run) |

Reasoning-model deployments don't accept `temperature`, so LLM-dependent metrics vary slightly between runs. I report that instead of hiding it.

## What I'd do next

Replace the synthetic corpus with a licensed one, add a semantic-cache for repeated queries, and move the golden set to an evaluator that can score groundedness.

## Links

- Live demo, README and screenshots: see the repository.
- Design document with 11 Mermaid diagrams: [`docs/SDD.md`](SDD.md)
- Requirements: [`docs/SRS.md`](SRS.md)
