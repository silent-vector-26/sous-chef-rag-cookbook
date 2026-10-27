# Software Design Document — Sous-chef (RAG Cookbook)

Companion to the [SRS](SRS.md). The SRS says *what* the system must do; this document says *how* it is built and *why* the design choices were made. Requirement IDs (FR-n / NFR-n) refer to the SRS.

## 1. Design goals

| Goal | Consequence |
|---|---|
| Runs offline for dev/CI (FR-11) | Retrieval sits behind a `Store` protocol with a local and an Azure implementation |
| Keyless security (NFR-1) | Entra ID everywhere; `DefaultAzureCredential`; local auth disabled on every service |
| Trustworthy answers (FR-2, FR-3) | Grounded prompt, citations, refusal path, evaluation harness |
| Deterministic core logic (FR-5) | Ingredient ranking is plain code, not an LLM call |
| Low idle cost (NFR-7) | AI Search Free tier, Container Apps scale to zero |

## 2. Architecture overview

### 2.1 Use cases

```mermaid
flowchart LR
    Cook([Home cook])
    Dev([Developer / reviewer])
    Cook --> UC1[Find recipes from my ingredients]
    Cook --> UC2[Ask the cookbook a question]
    Cook --> UC3[Upload fridge photo]
    Cook --> UC4[Run research agent]
    Dev --> UC5[Run evaluation]
    Dev --> UC6[Deploy with azd]
    UC1 -.includes.-> UC7[Apply dietary filters]
    UC2 -.includes.-> UC8[Screen input for safety]
    UC1 -.includes.-> UC8
```

### 2.2 System context

```mermaid
flowchart TB
    User([User]) --> UI[Streamlit UI<br/>Container Apps]
    UI --> Safety[Content Safety<br/>Prompt Shields]
    UI --> Core[RAG core<br/>ask / cook_with / agent]
    Core --> LLM[Azure OpenAI<br/>chat + vision]
    Core --> Rank[Ingredient ranker<br/>fewest-missing]
    Core --> Store{{Store interface}}
    Store --> Search[(Azure AI Search<br/>hybrid + semantic)]
    Store --> Local[(LocalStore<br/>TF-IDF, offline)]
    Ingest[Ingestion pipeline] --> Search
    Ingest --> LLM
    UI -. OpenTelemetry .-> AI[Application Insights]
    MI[Managed identity] -. RBAC .-> LLM
    MI -. RBAC .-> Search
    MI -. RBAC .-> Safety
```

### 2.3 Component view

```mermaid
flowchart LR
  UI[Streamlit UI / CLI] --> RAG[rag.py<br/>ask, cook_with]
  UI --> AGT[agent.py<br/>tool loop]
  RAG --> SAFE[safety.py]
  RAG --> LLM[llm.py]
  AGT --> LLM
  RAG --> ING[ingredient_search.py<br/>rank, shopping, unlocks]
  RAG --> ST{{Store protocol}}
  AGT --> RAG
  ST --> LS[LocalStore<br/>TF-IDF, in-memory]
  ST --> AS[AzureStore]
  AS --> SRCH[(Azure AI Search)]
  AS --> AOAI[(Azure OpenAI<br/>embeddings)]
  LLM --> AOAI2[(Azure OpenAI<br/>chat + vision)]
  SAFE --> CS[(Content Safety)]
```

The backend is selected by `config.backend()` (`BACKEND=local|azure`) and `store.get_store()`. The RAG layer uses the shared `Store` protocol; generation and safety helpers choose heuristic or service-backed behavior. The UI also gates vision and agent features by backend.

## 3. Module design

| Module | Responsibility | Key interface |
|---|---|---|
| `models.py` | Dataclasses `Recipe`, `Citation`, `Answer`, `Match` | — |
| `config.py` | Reads env / `.env`; selects backend | `backend()`, `get(key, default)` |
| `normalize.py` | Canonical ingredient names: lowercase, singularize, fold synonyms, drop quantities | `normalize(name)`, `normalize_list` |
| `extract.py` | Heuristic ingredient extraction from recipe text (ingestion) | `extract_ingredients` |
| `store.py` | Retrieval abstraction and both implementations | `Store.search`, `Store.candidates_by_ingredients` |
| `ingredient_search.py` | Ranking by missing ingredients, shopping list, unlock tips | `rank_by_missing`, `shopping_list`, `unlock_suggestions` |
| `rag.py` | Orchestrates safety, retrieval and generation | `ask`, `cook_with` |
| `llm.py` | Azure OpenAI calls: pantry parsing (JSON mode), ingredient extraction, image ingredient extraction | `chat`, `parse_pantry`, `describe_image_ingredients` |
| `agent.py` | Tool-calling loop over `search_recipes` and `find_by_ingredients`, returns a tool trace | `run_agent` |
| `safety.py` | Prompt Shields + harm categories (Azure) or regex heuristic (local) | `check_input` |
| `ingest/` | `build_dataset.py` builds `data/recipes.json`; `index_azure.py` creates the index and uploads embedded documents | CLI |
| `eval/run_eval.py` | Golden-set metrics | CLI |

```mermaid
classDiagram
  class Store {
    <<protocol>>
    +search(query, top, diet) list
    +candidates_by_ingredients(have, top) list
  }
  class LocalStore
  class AzureStore {
    +embed(text) list
  }
  Store <|.. LocalStore
  Store <|.. AzureStore
  class Recipe {
    id; title; source; page
    text; ingredients; ingredient_lines; tags
  }
  Store ..> Recipe
```

## 4. Key design decisions

| # | Decision | Alternatives | Rationale |
|---|---|---|---|
| D1 | Ingredient ranking is deterministic code over retrieved candidates | Ask the LLM to rank | FR-5 and NFR-4 demand exact ordering; code is testable and free of hallucination. The LLM is only used to *parse* the pantry text |
| D2 | Ranking key `(len(missing), -len(have), -retrieval_score, title)` | Score-first | Matches the user's goal: cook with the fewest extra purchases; ties favour recipes that use more of what is owned |
| D3 | Staples (salt, pepper, water, oil) never count as missing | Count everything | Avoids useless shopping suggestions |
| D4 | Candidate retrieval uses an OData filter `search.in(i, '…', ',')` over `ingredients`, then ranks in Python | Pure vector search | Guarantees every candidate contains at least one owned ingredient; keeps ranking independent of embedding quality |
| D5 | Hybrid query (BM25 + vector) with semantic reranking for Q&A | Vector only | Keyword exactness plus semantic recall; the reranker supplies a relevance signal, not a probability of correctness |
| D6 | Refusal is enforced twice: local score threshold (`MIN_LOCAL_SCORE`) and an exact refusal phrase in the system prompt, detected in the reply | Prompt only | Defence in depth; refusal returns no citations and `grounded=False` |
| D7 | Citations are derived from `[rNNN]` tags present in the reply, falling back to the top hit | Cite all retrieved | Avoids listing every candidate, but fallback does not prove that the model used the source |
| D8 | Entra-only auth with a user-assigned managed identity | Keys in env vars | NFR-1; no secrets to leak or rotate. `AZURE_CLIENT_ID` makes `DefaultAzureCredential` pick the user-assigned identity |
| D9 | Current chat deployment (`gpt-5.4-mini`) with no `temperature` argument | Other regionally available chat models | The selected deployment rejected explicit `temperature`; model availability and parameter support must be checked for each deployment |
| D10 | AI Search Free tier by default, `searchSku` / `searchLocation` parameters | Basic | NFR-7. Dataset is far below 50 MB. Region is a parameter because capacity varies (eastus2 was exhausted) |
| D11 | Scale-to-zero Container App with remote ACR build | Always-on, App Service | Near-zero idle cost; no local Docker needed for deploy |

## 5. Data design

### 5.1 Logical model

```mermaid
erDiagram
    RECIPE ||--o{ INGREDIENT_LINE : has
    RECIPE ||--o{ INGREDIENT : requires
    RECIPE ||--o{ TAG : labelled
    RECIPE {
        string id PK
        string title
        string source
        int page
        string text
        vector content_vector
    }
    INGREDIENT_LINE { string raw }
    INGREDIENT { string canonical_name }
    TAG { string name }
```

### 5.2 Ingestion pipeline

```mermaid
flowchart LR
    A[Raw recipes JSON / cookbook text] --> B[Extract ingredient lines]
    B --> C{Mode}
    C -->|offline| D[Heuristic extractor]
    C -->|--llm| E[LLM structured extraction]
    D --> F[Normalize: singular, synonyms]
    E --> F
    F --> G[recipes.json]
    G --> H[Embed title + ingredients + method]
    H --> I[("AI Search index<br/>text, ingredients[], tags[], vector")]
```

### 5.3 Search index schema

Search index `recipes` (created by `ingest/index_azure.py`):

| Field | Type | Attributes |
|---|---|---|
| `id` | String | key |
| `title` | String | searchable |
| `source` | String | filterable |
| `page` | Int32 | filterable |
| `text` | String | searchable |
| `ingredients` | Collection(String) | searchable, filterable (canonical names) |
| `ingredient_lines` | Collection(String) | display only |
| `tags` | Collection(String) | searchable, filterable (diet filters) |
| `content_vector` | Collection(Single), 1536 dims | HNSW profile `hnsw-profile` |

- **Embedding input:** `"{title}. Ingredients: {…}. {text}"` using `text-embedding-3-small`.
- **Semantic configuration:** `recipes-semantic` (title → `title`, content → `text`, keywords → `ingredients`).
- **Offline equivalent:** `LocalStore` builds an in-memory TF-IDF over the same fields from `data/recipes.json`.

## 6. Runtime design

### 6.1 Ingredient search (`rag.cook_with`)

```mermaid
sequenceDiagram
  actor U as User
  participant R as rag.cook_with
  participant S as safety
  participant L as llm.parse_pantry
  participant St as Store
  participant I as ingredient_search
  U->>R: "I have chicken, potatoes and carrots"
  R->>S: check_input
  S-->>R: allowed
  R->>L: parse (JSON mode)
  L-->>R: [chicken, potato, carrot]
  R->>St: candidates_by_ingredients(have, 100)
  St-->>R: recipes + scores
  R->>I: rank_by_missing (full pool)
  I-->>R: ranked matches
  R->>I: shopping_list(shown), unlock_suggestions(pool)
  R-->>U: matches, shopping list, unlock tips
```

Unlock tips are computed over the full ranked pool, then the display list is trimmed to `limit`, so a suggestion can point at recipes not currently shown.

### 6.2 Grounded Q&A (`rag.ask`)

```mermaid
flowchart TD
  Q[Question] --> SF{safety.check_input}
  SF -- blocked --> B[Blocked answer]
  SF -- ok --> H[store.search top 4]
  H --> E{any hits?}
  E -- no --> RF[Refusal]
  E -- yes --> G[llm.chat with sources]
  G --> D{reply contains refusal phrase?}
  D -- yes --> RF
  D -- no --> C[Answer + citations]
```

### 6.3 Agent (`agent.py`)

A bounded tool-calling loop: the model may call `search_recipes` or `find_by_ingredients`, results are fed back, and the loop ends on a final message or the step limit. Every tool call is recorded and shown in the UI as the trace.

### 6.4 Interface and bundled assets

The Streamlit interface combines a photo-mosaic hero, a featured gallery, pantry chips and free-text input. Filters are inline rather than in a sidebar. Each search result is a single image tile containing the title, missing-count badge and an HTML `<details>` section for coverage, owned/missing ingredients, instructions and source attribution.

The featured gallery reads cached `data/recipes.json` through `load_recipes()`, independently of the selected retrieval backend. It must not access `LocalStore.recipes` on a shared UI path; `AzureStore` only implements the retrieval protocol. UI regression tests cover initial load and filter reruns with both backend configurations.

Recipe images are keyed by ID (`app/static/img/<id>.webp`), embedded as data URIs and cached by the UI. The 205 illustrative images were generated once offline with `gpt-image-1-mini`, resized to 512px WebP and bundled with the container (about 5.2 MB). `ingest/generate_images.py` is an offline utility; runtime image generation is not required. The temporary generation resource was deleted, and the exact one-time spend was not measured.

Photo upload currently replaces the typed/chip ingredient list with detected ingredients; the lists are not merged. Dietary widgets constrain pantry results and Q&A retrieval, not the agent or featured gallery. Vision detections are shown in the result summary but cannot yet be corrected inline.

## 7. Security design

```mermaid
flowchart LR
  subgraph Identities
    MI[User-assigned managed identity<br/>Container App]
    DEV[Deploying user<br/>principalId]
  end
  MI -->|AcrPull| ACR[Container Registry]
  MI -->|Cognitive Services OpenAI User| AOAI[Azure OpenAI]
  MI -->|Search Index Data Reader| SRCH[AI Search]
  DEV -->|Search Index Data Contributor,<br/>Search Service Contributor| SRCH
  MI -->|Cognitive Services User| CS[Content Safety]
  DEV -->|OpenAI User, Content Safety User| AOAI
```

- `disableLocalAuth: true` on OpenAI, Search and Content Safety; ACR admin user disabled.
- Least privilege: the runtime app identity holds only AcrPull, Cognitive Services OpenAI User, Cognitive Services User and **Search Index Data Reader** (the app never writes to the index). Index creation and uploads need *Search Index Data Contributor* and *Search Service Contributor*, which are granted only to the deploying principal (the user locally, the CI identity in the pipeline).
- The CI identity has **Contributor** plus **Role Based Access Control Administrator** on the resource group; the RBAC role carries an ABAC condition that limits it to assigning/removing only the six roles above (no Owner, no privilege escalation).
- Prompt injection: Q&A and pantry-text parsing call `check_input`. With an Azure Content Safety endpoint configured, it runs Prompt Shields and harm analysis; otherwise it uses the local regex heuristic. The Q&A system prompt instructs the model to ignore instructions inside sources. `tests/test_injection.py` and the three injection cases in `eval/golden.json` cover selected attacks, not a complete adversarial assessment.
- Coverage boundary: the agent's top-level prompt, its direct search tool and image extraction do not all traverse this safety gate. Supplying `have` directly to `cook_with` skips pantry-text screening. Consistent entry-point protection is further production work.
- User-supplied values interpolated into OData filters are quote-escaped (`_esc`).
- No secrets in the repo; `.env.example` holds only endpoints and deployment names.

## 8. Deployment design

```mermaid
flowchart LR
  azd[azd provision / deploy] --> RG[Resource group]
  subgraph RG
    LAW[Log Analytics] --> AI[App Insights]
    ACR[Container Registry]
    ENV[Container Apps Environment] --> APP[Container App web<br/>minReplicas 0, port 8501]
    AOAI[Azure OpenAI<br/>gpt-5.4-mini, text-embedding-3-small]
    SRCH[AI Search Free]
    CS[Content Safety]
  end
  azd -- remote build --> ACR --> APP
```

- Single Bicep template at resource-group scope (`infra/main.bicep`), parameters mapped in `infra/main.parameters.json`.
- Parameters: `location`, `aiLocation`, `searchLocation`, `searchSku` (`free` default), `principalId`.
- Deploy flow: `azd provision` → `azd deploy` → `python -m ingest.index_azure` (needs the deployer RBAC roles; propagation can take minutes).
- CI/CD: a merge to `main` triggers `ci`; on success `deploy.yml` (`workflow_run`) logs in with GitHub OIDC to an Entra app (`gh-sous-chef-deploy`, federated credential for `refs/heads/main`, Contributor + a condition-constrained Role Based Access Control Administrator on the resource group so Bicep can create the role assignments), then runs the same provision → deploy → index steps plus an HTTP smoke test. Deploys are serialized (`concurrency`), and `principalType` is `ServicePrincipal` in CI so the pipeline identity also gets the data-plane roles needed for indexing.
- Repository variables: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_ENV_NAME`, `AZURE_LOCATION`, `AZURE_RESOURCE_GROUP`, `AZURE_SEARCH_LOCATION`, `AZURE_PRINCIPAL_ID`, and optional `AZURE_BUDGET_EMAIL`. The first client ID identifies the deployment identity in CI; the application uses its own managed identity at runtime.
- The Docker build copies the UI, images and `.streamlit/config.toml` along with the core and data. Deployment's HTTP 200 check confirms availability only; it does not exercise recipe tiles, Q&A, the agent or upload.
- Reference cost: see §9 (Cost optimization).

## 9. Cost optimization

The following are indicative USD planning estimates, not measured invoices or guaranteed current prices. Verify region-specific rates, free allowances and your subscription's usage in Azure Cost Management before deployment.

### 9.1 Cost drivers

| Resource | Billing model | Basic-tier baseline | Current design | Idle cost |
|---|---|---|---|---|
| Azure AI Search | Per hour per search unit | Basic: $0.10/h ≈ $73/month | **Free** tier (`searchSku=free`) | $0 |
| Container Registry | Per day + storage | Basic: ~$0.167/day ≈ $5/month | Basic, no admin user | ~$5/month |
| Container Apps | Per-second vCPU/memory + requests; monthly free grant | Always-on replica ≈ $5–15/month | `minReplicas: 0` (scale to zero) | ~$0 |
| Azure OpenAI | Per token | Pay per use | `gpt-5.4-mini` + `text-embedding-3-small`, GlobalStandard/Standard | $0 when unused |
| Content Safety | Per text record / API usage | Pay per use | Prompt Shields plus harm analysis on screened text paths | $0 when unused |
| Log Analytics / App Insights | Ingestion and retention | Pay per use, allowances vary | 30-day retention, demo volume | Usage-dependent |
| Managed identity, RBAC | Free | — | — | $0 |

Estimated idle baseline: **about $5/month**, mainly ACR Basic. Compute, builds, model calls, storage and telemetry can add charges. Recipe photographs are bundled assets, so viewing them adds no image-model inference charge; storage and delivery still use infrastructure.

### 9.2 Optimization decisions

| # | Measure | Effect | Trade-off |
|---|---|---|---|
| C1 | AI Search Free tier by default | Removes the paid Search baseline | 50 MB, 3 indexes, shared capacity, no SLA; semantic quota and idle-service lifecycle are subject to Azure limits; cannot be upgraded in place |
| C2 | Container App scales to zero | No compute cost while idle | Cold start on the first request (a gateway timeout is possible) |
| C3 | Small chat model (`gpt-5.4-mini`) and small embeddings (`text-embedding-3-small`, 1536 dims) | Lower-cost model selection, evaluated on the demo set | No exhaustive model/cost comparison was performed |
| C4 | Ranking, shopping list and unlock tips in code, not LLM calls | Zero tokens for the core feature, plus determinism | — |
| C5 | One chat call for Q&A generation or pantry parsing; agent capped at 5 iterations | Limits ordinary request complexity | Q&A also embeds the query; agent iterations can contain multiple tool calls, so this is not a hard spend cap |
| C6 | Only the top 4 sources are put into the prompt | Smaller prompts | Possible recall loss on broad questions |
| C7 | Embeddings are computed once at ingest, not per document at query time (only the query is embedded) | One embedding call per search | Re-ingest needed when the corpus changes |
| C8 | Content Safety is skipped by the offline backend | Free dev/CI | Heuristic only |
| C9 | ACR Basic with remote build | No build agent or Docker needed locally | ~$5/month floor |
| C10 | Single resource group, one `azd down --purge` | Clean teardown between demos | Re-provision and re-index to restore |

### 9.3 Further options

| Option | Saves | When to use |
|---|---|---|
| Delete the registry after deploy and pull from a public image | ~$5/month | Only if the registry is not needed again |
| Lower OpenAI deployment capacity (currently 30) | Nothing directly (pay per token) but limits runaway spend | Always reasonable for demos |
| **Implemented:** resource-group budget (`infra/main.bicep`: $20/month; alerts at 50/80/100% actual and 100% forecast; set `AZURE_BUDGET_EMAIL` to enable) | Notifies about spend; does not cap or stop it | Always |
| **Production recommendation:** `searchSku=basic` (or higher) and `minReplicas: 1` | Increases recurring cost | Removes scale-to-zero cold starts and adds Search capacity; SLA eligibility depends on tier and replica configuration |
| Prompt caching and shorter prompts | Fewer input tokens | When traffic grows |
| Cache frequent query embeddings | Fewer embedding calls | When traffic grows |

## 10. Observability design (NFR-6)

OpenTelemetry spans are created by `ragcookbook/tracing.py` (a no-op when the SDK is absent). When `APPLICATIONINSIGHTS_CONNECTION_STRING` is set, `azure-monitor-opentelemetry` exports them to Application Insights, where Azure SDK and HTTP dependency calls appear as children.

| Span | Attributes |
|---|---|
| `rag.ask` | `rag.question_chars`, `rag.diet`, `rag.grounded`, `rag.citations`, `rag.outcome` (answered/refused/blocked) |
| `safety.check_input`, `rag.retrieve` | `rag.top`, `rag.hits` |
| `rag.cook_with` → `rag.candidates`, `rag.rank` | `pantry.items`, `rag.results` |
| `llm.chat` | `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` |
| `agent.run` → `agent.step` → `agent.tool` | `agent.tool_calls`, `agent.tool.name` |

Privacy: spans record sizes, counts, and outcomes only, never raw questions or pantry text.

Useful KQL (Application Insights → Logs). For workspace-based resources the same data is in `AppDependencies` (`Name`, `DurationMs`, `Properties`) in Log Analytics.

Verified live (spans from `ask`, `cook_with` and the agent against the deployed Azure resources):

| Name | Count | p50 (ms) |
|---|---|---|
| `rag.ask` | 3 | 3089 |
| `safety.check_input` | 3 | 1133 |
| `rag.retrieve` | 3 | 474 |
| `agent.step` | 2 | 1902 |
| `POST /openai/deployments/gpt-5.4-mini/chat/completions` | 12 | 1120 |
| `POST /indexes('recipes')/docs/search.post.search` | 14 | 174 |

Note: telemetry can take a few minutes to appear, and `az monitor app-insights query` may lag behind the workspace; query Log Analytics directly when verifying.

```kusto
// Latency and outcome by operation
dependencies
| where name startswith "rag." or name startswith "agent." or name == "llm.chat"
| summarize count(), p50=percentile(duration, 50), p95=percentile(duration, 95) by name

// Refusal / block rate
dependencies | where name == "rag.ask"
| summarize n=count() by outcome=tostring(customDimensions["rag.outcome"])

// Token usage per day
dependencies | where name == "llm.chat"
| summarize tokens_in=sum(toint(customDimensions["gen_ai.usage.input_tokens"])),
            tokens_out=sum(toint(customDimensions["gen_ai.usage.output_tokens"])) by bin(timestamp, 1d)
```

## 11. Quality and testing design

```mermaid
flowchart LR
    G[eval/golden.json<br/>QA + pantry cases] --> H[run_eval]
    H --> M1["Recall@5, MRR"]
    H --> M2[Citation accuracy]
    H --> M3[Refusal rate]
    H --> M4[Pantry top-1, sort order]
    M1 & M2 & M3 & M4 --> R[eval/results/&lt;backend&gt;.json]
    R --> C[Compare strategies: local vs hybrid vs semantic]
```

| Layer | Approach |
|---|---|
| Unit | `tests/test_core.py`: normalization, pantry parsing, ranking, filters, unlock tips, grounding, injection (offline, deterministic) |
| Evaluation | `eval/run_eval.py` on `eval/golden.json`: recall@k, citation rate, refusal rate, pantry sort correctness (NFR-2…4) |
| UI regression | `tests/test_ui.py`: Streamlit initial render and dietary-widget rerun with store mocks that expose only the shared interface |
| CI | GitHub Actions: UI + dev dependencies, pytest, local evaluation, `az bicep build` |
| Live | Azure evaluation for retrieval/answer metrics; interactive browser checks for pantry, Q&A, agent and upload |

The evaluator's `citation_accuracy` is an expected-source hit rate, not claim-level groundedness. Its success exit code means metrics were computed, not that quality targets passed. Small synthetic data, citation fallback behavior and empty-list sorting can make individual metrics optimistic; see [evaluation methodology](../cookbook/08-evaluation.md).

### Live UI check, 2026-10-27

Browser checks against the deployed Azure app verified the homepage gallery, empty-input validation, pantry chips, ascending missing counts, keyboard expansion of recipe details inside tiles, free-text pantry entry, vegetarian filtering, a zero-missing limit, cited carbonara Q&A, refusal of an unrelated physics question, and an agent answer with a visible `find_by_ingredients` tool call. Screenshots in `docs/img/` were refreshed from the live interface.

The photo path successfully extracted chicken, potato and carrot from a generated plated-food PNG and returned recipes. A repeated upload later failed with HTTP 400 before inference ([#13](https://github.com/silent-vector-26/sous-chef-rag-cookbook/issues/13)); upload reliability is therefore an open finding, not a clean pass. The fixture was not a real fridge photograph. These are workflow smoke checks, not a fresh golden-set evaluation or a vision accuracy benchmark.

## 12. Known limitations and risks

| Item | Impact | Mitigation / next step |
|---|---|---|
| LLM-dependent metrics vary between runs (citation accuracy 0.86–1.00 over 5 runs) because gpt-5.x rejects `temperature` | Flaky eval numbers | Report ranges; add more cases and run several times |
| Free Search tier: shared capacity, no SLA, service quotas and idle-service lifecycle limits | Latency variance, possible index unavailability | Check current Azure limits; re-index when required; use a paid tier for real workloads |
| Scale to zero | Cold-start delay on the first request | Accepted for a demo; `minReplicas` stays 0 (set to 1 only for production use) |
| Corpus is synthetic (205 recipes; 180 LLM-generated) | Metrics are optimistic vs. real-world data | Ingest licensed or public-domain sources via `ingest/build_dataset.py --llm` |
| Heuristic ingredient extraction | Misses unusual phrasing | LLM-assisted extraction at ingest time |
| Inconsistent safety/dietary coverage across entry points | UI controls are not universal guarantees | Extend consistent controls before production; document current scope |
| Generated imagery and untested recipes | Visuals can differ from instructions; dietary tags are not certified | Clearly disclose provenance; do not use for medical/allergy decisions |
| Intermittent photo-upload HTTP 400 observed in live checks | Some uploads fail before ingredient extraction | Investigate session/upload behavior in [#13](https://github.com/silent-vector-26/sous-chef-rag-cookbook/issues/13); no root cause confirmed yet |

## 13. Traceability (design → requirements)

| Design element | Satisfies |
|---|---|
| `Store` protocol + `LocalStore` | FR-11, NFR-5 |
| D1–D4, `ingredient_search.py` | FR-4, FR-5, FR-6, FR-7, NFR-4 |
| D5–D7, `rag.ask` | FR-2, FR-3, NFR-3 |
| `safety.py`, §7 | FR-10 |
| `llm.describe_image_ingredients` | FR-8 |
| `agent.py` | FR-9 |
| `ingest/`, §5 | FR-1 |
| `eval/run_eval.py`, §11 | FR-12, NFR-2…4 |
| §7 identities and RBAC | NFR-1 |
| App Insights in §8, tracing in §10 | NFR-6 |
| D10, D11, §8, §9 | NFR-7, NFR-8 |
