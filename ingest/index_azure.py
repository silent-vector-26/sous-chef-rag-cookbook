"""Create the AI Search index and upload recipes with embeddings.

    python -m ingest.index_azure
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from azure.search.documents import SearchClient  # noqa: E402
from azure.search.documents.indexes import SearchIndexClient  # noqa: E402
from azure.search.documents.indexes.models import (  # noqa: E402
    HnswAlgorithmConfiguration, SearchableField, SearchField, SearchFieldDataType, SearchIndex,
    SemanticConfiguration, SemanticField, SemanticPrioritizedFields, SemanticSearch, SimpleField,
    VectorSearch, VectorSearchProfile,
)

from ragcookbook.store import AzureStore, load_recipes  # noqa: E402

DIMS = 1536  # text-embedding-3-small


def build_index(name: str) -> SearchIndex:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="page", type=SearchFieldDataType.Int32, filterable=True),
        SearchableField(name="text", type=SearchFieldDataType.String),
        SearchField(name="ingredients", type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=True, filterable=True, facetable=True),
        SimpleField(name="ingredient_lines", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
        SearchField(name="tags", type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    filterable=True, facetable=True),
        SearchField(name="content_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True, vector_search_dimensions=DIMS, vector_search_profile_name="hnsw-profile"),
    ]
    return SearchIndex(
        name=name,
        fields=fields,
        vector_search=VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hnsw")],
            profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw")],
        ),
        semantic_search=SemanticSearch(configurations=[SemanticConfiguration(
            name="recipes-semantic",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="title"),
                content_fields=[SemanticField(field_name="text")],
                keywords_fields=[SemanticField(field_name="ingredients")],
            ),
        )]),
    )


def main() -> None:
    store = AzureStore()
    SearchIndexClient(store.endpoint, store.cred).create_or_update_index(build_index(store.index_name))
    docs = []
    for r in load_recipes():
        docs.append({
            "id": r.id, "title": r.title, "source": r.source, "page": r.page, "text": r.text,
            "ingredients": r.ingredients, "ingredient_lines": r.ingredient_lines, "tags": r.tags,
            "content_vector": store.embed(f"{r.title}. Ingredients: {', '.join(r.ingredients)}. {r.text}"),
        })
    SearchClient(store.endpoint, store.index_name, store.cred).upload_documents(docs)
    print(f"indexed {len(docs)} recipes into '{store.index_name}'")


if __name__ == "__main__":
    main()
