# 🍳 The RAG Cookbook — Sous-chef

[![ci](https://github.com/silent-vector-26/sous-chef-rag-cookbook/actions/workflows/ci.yml/badge.svg)](https://github.com/silent-vector-26/sous-chef-rag-cookbook/actions/workflows/ci.yml)

A recipe RAG app **and** a technical cookbook of RAG techniques, built on Azure AI Search + Azure OpenAI.

- 🥕 **Cook with what you have** — "I have chicken, potatoes and carrots" → recipes ranked by the *fewest ingredients you still need to buy*, with a shopping list and "buy X to unlock N more recipes" tips.
- 💬 **Ask the cookbook** — grounded answers with citations (book + page) and an honest "I don't know".
- 📸 **Fridge photo** (multimodal) and 🧭 **research agent** (tool-calling agentic RAG).
- 🛡️ Prompt Shields / Content Safety, Entra-only auth, evaluation harness, `azd` deploy.

```mermaid
flowchart LR
    U([User]) --> UI[Streamlit] --> SAFE[Safety] --> CORE[RAG core]
    CORE --> RANK[Fewest-missing ranker]
    CORE --> AIS[(AI Search: BM25 + vector + semantic)]
    CORE --> AOAI[Azure OpenAI]
```
Full requirements and diagrams: [`docs/SRS.md`](docs/SRS.md).

## Quick start (offline, no Azure needed)
```powershell
pip install -e ".[ui,dev]"
python -m ingest.build_dataset
python -m ragcookbook.cli cook "I have chicken, potatoes and carrots"
python -m ragcookbook.cli ask "how do I make carbonara"
streamlit run app/streamlit_app.py
pytest
python -m eval.run_eval
```
Sample output:
```
You have: chicken, potato, carrot
Roast Chicken with Potatoes and Carrots  [3/5]  missing: onion, thyme
Honey Mustard Chicken and Carrots        [2/4]  missing: honey, mustard
...
```

## Azure mode
```powershell
azd up                              # OpenAI, AI Search, Content Safety, App Insights, Container App + RBAC
copy .env.example .env              # set BACKEND=azure and endpoints from `azd env get-values`
pip install -e ".[azure,ui]"
python -m ingest.index_azure        # create index + upload embeddings
streamlit run app/streamlit_app.py
```
You need RBAC on your own identity for local runs: *Cognitive Services OpenAI User*, *Search Index Data Contributor*, *Search Service Contributor*.
Cost: AI Search Basic is billed hourly — `azd down` when finished.

## The cookbook (one technique per recipe)
| # | Recipe |
|---|---|
| 01 | [Chunking & structured extraction](cookbook/01-chunking-and-extraction.md) |
| 02 | [Hybrid search](cookbook/02-hybrid-search.md) |
| 03 | [Semantic reranking](cookbook/03-semantic-reranking.md) |
| 04 | [Citations & refusal](cookbook/04-citations-and-refusal.md) |
| 05 | [Ingredient search & domain ranking](cookbook/05-ingredient-search.md) |
| 06 | [Multimodal](cookbook/06-multimodal.md) |
| 07 | [Agentic RAG](cookbook/07-agentic-rag.md) |
| 08 | [Evaluation](cookbook/08-evaluation.md) |
| 09 | [Safety](cookbook/09-safety.md) |

## Evaluation (offline baseline)
| metric | local |
|---|---|
| retrieval recall@5 / MRR | 1.00 / 1.00 |
| citation accuracy | 1.00 |
| refusal on unanswerable | 1.00 |
| pantry top-1 / sorted by missing | 1.00 / 1.00 |

The sample set is small by design; add your own cases to `eval/golden.json` and record Azure (hybrid + semantic) results next to it.

## Data
`data/recipes.raw.json` contains 25 classic recipes written in original wording (no copyrighted text). To scale up, ingest public-domain cookbooks (e.g. Project Gutenberg) and use `python -m ingest.build_dataset --llm` for structured extraction; check each source's license.

## Atlassian MCP (Jira / Confluence)
`.mcp.json` registers the official [Atlassian remote MCP server](https://support.atlassian.com/atlassian-ai-gateway/docs/get-started-with-the-atlassian-remote-mcp-server/) (`https://mcp.atlassian.com/v2/mcp`) so Copilot sessions can read Jira work items and Confluence pages. Sign in once via OAuth (in the Copilot app: Settings → project → Repository customizations → MCP servers → Sign in). No secrets are stored in the repo.

## Contributing & license
See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and [CHANGELOG.md](CHANGELOG.md). Released under the [MIT License](LICENSE).

## Layout
`docs/` SRS · `src/ragcookbook/` core · `ingest/` dataset + index · `app/` UI · `eval/` metrics · `cookbook/` recipes · `infra/` Bicep · `tests/`

> Azure-mode code paths (AI Search, OpenAI, Content Safety, agent) are written against the documented SDKs but were not exercised against live resources in the authoring environment; the offline path, tests, UI and Bicep compilation were verified.
