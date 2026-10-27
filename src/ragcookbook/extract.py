"""Turn raw ingredient lines ('2 tbsp olive oil, divided') into canonical names ('oil')."""
import re

from .normalize import normalize

UNITS = {
    "cup", "cups", "tbsp", "tsp", "tablespoon", "tablespoons", "teaspoon", "teaspoons",
    "lb", "lbs", "pound", "pounds", "oz", "ounce", "ounces", "g", "kg", "ml", "l",
    "can", "cans", "clove", "cloves", "slice", "slices", "stalk", "stalks", "handful",
    "pinch", "whole", "fillet", "fillets", "piece", "pieces", "bunch", "head", "sprig", "sprigs",
}
DESCRIPTORS = {"ripe", "fresh", "cooked", "large", "small", "medium", "chopped", "diced",
               "sliced", "of", "thinly", "peeled", "hard-boiled", "melted", "frozen"}


def extract_ingredient(line: str) -> str:
    base = line.split(",")[0].lower()
    tokens = [t for t in re.split(r"\s+", base) if t]
    out = []
    for t in tokens:
        if re.fullmatch(r"[\d/.\-]+", t) or t in UNITS or t in DESCRIPTORS:
            continue
        out.append(t)
    return normalize(" ".join(out))


def extract_all(lines: list[str]) -> list[str]:
    seen: list[str] = []
    for line in lines:
        name = extract_ingredient(line)
        if name and name not in seen:
            seen.append(name)
    return seen
