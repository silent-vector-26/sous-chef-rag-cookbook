"""Retrieval backends. Both expose the same interface so the RAG layer is backend-agnostic.

LocalStore  - offline TF-IDF keyword retrieval (demo/tests, no Azure needed)
AzureStore  - Azure AI Search hybrid (BM25 + vector) with semantic reranker and filters
"""
import json
import math
import re
from pathlib import Path
from typing import Protocol

from . import config
from .models import Recipe
from .normalize import normalize_list

DATA = Path(__file__).resolve().parents[2] / "data" / "recipes.json"
_TOKEN = re.compile(r"[a-z]+")


class Store(Protocol):
    def search(self, query: str, top: int = 5, diet: list[str] | None = None) -> list[tuple[Recipe, float]]: ...
    def candidates_by_ingredients(self, have: list[str], top: int = 50) -> list[tuple[Recipe, float]]: ...


def load_recipes(path: Path = DATA) -> list[Recipe]:
    return [Recipe.from_dict(d) for d in json.loads(path.read_text(encoding="utf-8"))]


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class LocalStore:
    def __init__(self, recipes: list[Recipe] | None = None):
        self.recipes = recipes if recipes is not None else load_recipes()
        self._docs = [
            _tokens(f"{r.title} {r.title} {' '.join(r.ingredients)} {r.text}") for r in self.recipes
        ]
        n = len(self._docs)
        df: dict[str, int] = {}
        for d in self._docs:
            for t in set(d):
                df[t] = df.get(t, 0) + 1
        self._idf = {t: math.log(1 + n / c) for t, c in df.items()}

    def _score(self, q_tokens: list[str], doc: list[str]) -> float:
        if not doc:
            return 0.0
        return sum(self._idf.get(t, 0) * (doc.count(t) / len(doc) ** 0.5) for t in q_tokens)

    def search(self, query, top=5, diet=None):
        q = _tokens(query)
        diet_set = {d.lower() for d in (diet or [])}
        scored = []
        for r, d in zip(self.recipes, self._docs):
            if diet_set and not diet_set <= {t.lower() for t in r.tags}:
                continue
            s = self._score(q, d)
            if s > 0:
                scored.append((r, s))
        return sorted(scored, key=lambda x: -x[1])[:top]

    def candidates_by_ingredients(self, have, top=50):
        have_set = set(normalize_list(have))
        out = []
        for r in self.recipes:
            overlap = len(have_set & set(r.ingredients))
            if overlap:
                out.append((r, float(overlap)))
        return sorted(out, key=lambda x: -x[1])[:top]


class AzureStore:
    """Azure AI Search store. Auth is Entra ID (managed identity / az login) — no keys."""

    def __init__(self):
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        from azure.search.documents import SearchClient
        from openai import AzureOpenAI

        cred = DefaultAzureCredential()
        self.index_name = config.get("AZURE_SEARCH_INDEX", "recipes")
        self.endpoint = config.get("AZURE_SEARCH_ENDPOINT")
        self.cred = cred
        self.client = SearchClient(self.endpoint, self.index_name, cred)
        self.aoai = AzureOpenAI(
            azure_endpoint=config.get("AZURE_OPENAI_ENDPOINT"),
            azure_ad_token_provider=get_bearer_token_provider(
                cred, "https://cognitiveservices.azure.com/.default"),
            api_version=config.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )
        self.embed_model = config.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

    def embed(self, text: str) -> list[float]:
        return self.aoai.embeddings.create(model=self.embed_model, input=text).data[0].embedding

    @staticmethod
    def _to_recipe(d: dict) -> Recipe:
        return Recipe(
            id=d["id"], title=d["title"], source=d["source"], page=d.get("page"),
            text=d["text"], ingredients=list(d["ingredients"]),
            ingredient_lines=list(d.get("ingredient_lines") or []), tags=list(d.get("tags") or []),
        )

    @staticmethod
    def _esc(v: str) -> str:
        return v.replace("'", "''")

    def search(self, query, top=5, diet=None):
        from azure.search.documents.models import VectorizedQuery

        flt = " and ".join(f"tags/any(t: t eq '{self._esc(d)}')" for d in (diet or [])) or None
        results = self.client.search(
            search_text=query,
            vector_queries=[VectorizedQuery(vector=self.embed(query), k_nearest_neighbors=50, fields="content_vector")],
            filter=flt,
            query_type="semantic",
            semantic_configuration_name="recipes-semantic",
            top=top,
        )
        return [(self._to_recipe(r), float(r.get("@search.reranker_score") or r["@search.score"])) for r in results]

    def candidates_by_ingredients(self, have, top=50):
        have = normalize_list(have)
        values = ",".join(h.replace(",", " ") for h in have)
        results = self.client.search(
            search_text=" ".join(have),
            filter=f"ingredients/any(i: search.in(i, '{self._esc(values)}', ','))",
            top=top,
        )
        return [(self._to_recipe(r), float(r["@search.score"])) for r in results]


def get_store() -> Store:
    return AzureStore() if config.backend() == "azure" else LocalStore()
