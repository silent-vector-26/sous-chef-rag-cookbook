"""Ingredient normalization: plural/synonym folding and pantry-staple handling."""
import re

# Assumed to be in every kitchen; never counted as "missing".
STAPLES = {"salt", "pepper", "water", "oil", "cooking oil", "black pepper"}

SYNONYMS = {
    "spud": "potato", "scallion": "green onion", "spring onion": "green onion",
    "capsicum": "bell pepper", "coriander": "cilantro", "aubergine": "eggplant",
    "courgette": "zucchini", "garbanzo": "chickpea", "minced beef": "ground beef",
    "ground meat": "ground beef", "plain flour": "flour", "all-purpose flour": "flour",
    "olive oil": "oil", "vegetable oil": "oil", "caster sugar": "sugar",
    "granulated sugar": "sugar", "chicken breast": "chicken", "chicken thigh": "chicken",
    "chicken breasts": "chicken", "chicken thighs": "chicken",
}

_IRREGULAR = {"tomatoes": "tomato", "potatoes": "potato", "leaves": "leaf",
              "loaves": "loaf", "cherries": "cherry", "berries": "berry"}
_NO_STRIP = {"hummus", "couscous", "asparagus", "molasses", "swiss", "lemongrass"}


def _singular(word: str) -> str:
    if word in _IRREGULAR:
        return _IRREGULAR[word]
    if word in _NO_STRIP or len(word) <= 3 or word.endswith("ss"):
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith(("ches", "shes", "xes")):
        return word[:-2]
    if word.endswith("s"):
        return word[:-1]
    return word


def normalize(name: str) -> str:
    n = re.sub(r"\([^)]*\)", " ", name.lower())
    n = re.sub(r"[^a-z\- ]", " ", n)
    n = " ".join(n.split())
    n = " ".join(_singular(w) for w in n.split())
    n = SYNONYMS.get(n, n)
    return n


def normalize_list(names: list[str]) -> list[str]:
    seen: list[str] = []
    for raw in names:
        n = normalize(raw)
        if n and n not in seen:
            seen.append(n)
    return seen


def is_staple(name: str) -> bool:
    return normalize(name) in {normalize(s) for s in STAPLES}
