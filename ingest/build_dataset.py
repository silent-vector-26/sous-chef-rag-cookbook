"""Build data/recipes.json from data/recipes.raw.json (offline, heuristic extraction).

For messy real-world text (e.g. Project Gutenberg cookbooks) use the LLM extractor:
    python -m ingest.build_dataset --llm
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ragcookbook.extract import extract_all  # noqa: E402

SOURCE = "Sample Kitchen Companion (original wording, classic recipes)"


def llm_extract(lines: list[str]) -> list[str]:
    from ragcookbook.llm import extract_ingredients_llm

    return extract_ingredients_llm(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="use Azure OpenAI structured extraction")
    args = ap.parse_args()

    raw = json.loads((ROOT / "data" / "recipes.raw.json").read_text(encoding="utf-8"))
    out = []
    for r in raw:
        ingredients = llm_extract(r["ingredient_lines"]) if args.llm else extract_all(r["ingredient_lines"])
        out.append({**r, "source": SOURCE, "ingredients": ingredients})
    (ROOT / "data" / "recipes.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {len(out)} recipes -> data/recipes.json")


if __name__ == "__main__":
    main()
