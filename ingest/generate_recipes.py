"""Generate additional original-wording recipes with Azure OpenAI (synthetic data, no copyrighted text).

    BACKEND=azure python -m ingest.generate_recipes --per-theme 12

Appends to data/recipes.raw.json (ids continue from the highest existing id). Re-run
`python -m ingest.build_dataset` afterwards, then `python -m ingest.index_azure`.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ragcookbook import llm  # noqa: E402

THEMES = [
    "weeknight chicken and poultry dishes", "beef, pork and lamb mains", "fish and seafood",
    "vegetarian mains", "vegan dishes", "soups and stews", "pasta, noodles and rice dishes",
    "salads and vegetable sides", "breakfast and brunch", "breads, baking and desserts",
    "Mexican and Latin American", "Indian and South Asian", "East and Southeast Asian",
    "Mediterranean and Middle Eastern", "sandwiches, snacks and sauces",
]
MEAT = re.compile(r"chicken|beef|pork|lamb|bacon|ham\b|sausage|turkey|duck|fish|salmon|tuna|\bcod\b|shrimp|prawn|crab|"
                  r"anchov|steak|mince|veal|chorizo|gelatin|lard|clam|mussel|oyster|scallop|squid|calamari|lobster|"
                  r"octopus|sardine|mackerel|trout|halibut|tilapia|haddock|snapper|bass\b|meatball|pepperoni|"
                  r"prosciutto|pancetta|salami|brisket|\bribs?\b|sirloin|tenderloin|oxtail|goat|venison|rabbit|"
                  r"bone broth|kielbasa|hot dog|jerky", re.I)
ANIMAL = re.compile(r"milk|butter|cheese|cream|yogh?urt|egg|honey|parmesan|mayonnaise|ghee|feta|mozzarella|paneer", re.I)
GLUTEN = re.compile(r"flour|bread|pasta|spaghetti|noodle|couscous|bulgur|barley|breadcrumb|tortilla|pita|"
                    r"soy sauce|crust|pastry|macaroni|lasagn", re.I)
DAIRY = re.compile(r"milk|butter|cheese|cream|yogh?urt|ghee|parmesan|feta|mozzarella|paneer", re.I)

PROMPT = (
    "Write {n} DIFFERENT, original home-cooking recipes for the theme: {theme}. Use your own wording. "
    'Return JSON {{"recipes": [{{"title": str, "ingredient_lines": [str, ...], "text": str}}]}}. '
    "ingredient_lines look like '2 carrots, sliced' or '1 lb chicken thighs' or 'salt' (5-10 lines). "
    "text is the method in 2-4 sentences with times and temperatures. Avoid these existing titles: {existing}."
)


def derive_tags(lines: list[str]) -> list[str]:
    blob = " ".join(lines)
    tags = []
    if not MEAT.search(blob):
        tags.append("vegetarian")
        if not ANIMAL.search(blob):
            tags.append("vegan")
    if not GLUTEN.search(blob):
        tags.append("gluten-free")
    if not DAIRY.search(blob):
        tags.append("dairy-free")
    return tags


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-theme", type=int, default=12)
    ap.add_argument("--retag", action="store_true", help="re-derive tags for generated recipes (id > r025) and exit")
    args = ap.parse_args()

    path = ROOT / "data" / "recipes.raw.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    if args.retag:
        for r in raw:
            if int(r["id"][1:]) > 25:
                r["tags"] = derive_tags(r["ingredient_lines"])
        path.write_text(json.dumps(raw, indent=1, ensure_ascii=False), encoding="utf-8")
        print("retagged")
        return
    seen = {r["title"].lower() for r in raw}
    next_id = max(int(r["id"][1:]) for r in raw) + 1
    page = max(r["page"] for r in raw)

    for theme in THEMES:
        existing = ", ".join(sorted(seen)[:60])
        out = llm.chat([{"role": "user", "content": PROMPT.format(n=args.per_theme, theme=theme, existing=existing)}],
                       json_mode=True)
        added = 0
        for r in json.loads(out).get("recipes", []):
            title = r.get("title", "").strip()
            lines = [str(x).strip() for x in r.get("ingredient_lines", []) if str(x).strip()]
            if not title or title.lower() in seen or len(lines) < 3 or not r.get("text"):
                continue
            seen.add(title.lower())
            page += 3
            raw.append({"id": f"r{next_id:03d}", "title": title, "page": page,
                        "tags": derive_tags(lines), "ingredient_lines": lines, "text": r["text"].strip()})
            next_id += 1
            added += 1
        print(f"{theme}: +{added}")

    path.write_text(json.dumps(raw, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"total recipes: {len(raw)}")


if __name__ == "__main__":
    main()
