"""Pure ranking logic for 'what can I cook with what I have' — no I/O, fully unit-testable."""
from collections import Counter

from .models import Match, Recipe
from .normalize import is_staple, normalize, normalize_list


def match_recipe(recipe: Recipe, have: list[str], retrieval_score: float = 0.0) -> Match:
    have_set = set(normalize_list(have))
    required = [i for i in normalize_list(recipe.ingredients) if not is_staple(i)]
    got = [i for i in required if i in have_set]
    missing = [i for i in required if i not in have_set]
    coverage = len(got) / len(required) if required else 0.0
    return Match(recipe, got, missing, coverage, retrieval_score)


def rank_by_missing(
    candidates: list[tuple[Recipe, float]],
    have: list[str],
    max_missing: int | None = None,
    diet: list[str] | None = None,
    limit: int = 10,
) -> list[Match]:
    """Fewest missing ingredients first; ties -> more owned ingredients, then retrieval score."""
    diet_set = {d.lower() for d in (diet or [])}
    matches = []
    for recipe, score in candidates:
        if diet_set and not diet_set <= {t.lower() for t in recipe.tags}:
            continue
        m = match_recipe(recipe, have, score)
        if not m.have:
            continue
        if max_missing is not None and len(m.missing) > max_missing:
            continue
        matches.append(m)
    matches.sort(key=lambda m: (len(m.missing), -len(m.have), -m.retrieval_score, m.recipe.title))
    return matches[:limit]


def shopping_list(matches: list[Match]) -> list[str]:
    seen: list[str] = []
    for m in matches:
        for i in m.missing:
            if i not in seen:
                seen.append(i)
    return seen


def unlock_suggestions(matches: list[Match], top: int = 3) -> list[tuple[str, int]]:
    """Which single purchase would make the most recipes fully cookable (missing==1 -> 0)."""
    counter: Counter[str] = Counter()
    for m in matches:
        if len(m.missing) == 1:
            counter[m.missing[0]] += 1
    return counter.most_common(top)


def parse_pantry_heuristic(text: str) -> list[str]:
    """Offline fallback for the LLM pantry parser: 'I have chicken, potatoes and carrots'."""
    t = text.lower()
    for lead in ("i have", "i've got", "i got", "we have", "got", "with", "using", "i only have"):
        if lead in t:
            t = t.split(lead, 1)[1]
            break
    t = t.replace(" and ", ",").replace(";", ",").replace("&", ",")
    parts = [p.strip(" .!?") for p in t.split(",")]
    return normalize_list([p for p in parts if p and len(p.split()) <= 3])
