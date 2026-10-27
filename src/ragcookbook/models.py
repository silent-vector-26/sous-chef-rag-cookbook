from dataclasses import dataclass, field


@dataclass
class Recipe:
    id: str
    title: str
    source: str  # book / dataset name, used for citations
    page: int | None
    text: str  # recipe instructions
    ingredients: list[str]  # normalized, lower-case canonical names
    ingredient_lines: list[str] = field(default_factory=list)  # as written
    tags: list[str] = field(default_factory=list)  # e.g. vegetarian, gluten-free

    @classmethod
    def from_dict(cls, d: dict) -> "Recipe":
        return cls(**d)


@dataclass
class Match:
    recipe: Recipe
    have: list[str]
    missing: list[str]
    coverage: float  # have / required
    retrieval_score: float = 0.0


@dataclass
class Citation:
    id: str
    title: str
    source: str
    page: int | None


@dataclass
class Answer:
    text: str
    citations: list[Citation]
    grounded: bool
