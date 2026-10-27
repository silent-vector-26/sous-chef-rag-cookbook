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
    if args.llm:  # extract once and cache in the raw file so offline/CI builds are deterministic
        from concurrent.futures import ThreadPoolExecutor

        todo = [r for r in raw if "ingredients" not in r]
        import time

        def extract_with_retry(r):
            for attempt in range(6):
                try:
                    return llm_extract(r["ingredient_lines"])
                except Exception:
                    if attempt == 5:
                        raise
                    time.sleep(5 * (attempt + 1))

        with ThreadPoolExecutor(max_workers=2) as pool:
            for r, names in zip(todo, pool.map(extract_with_retry, todo)):
                r["ingredients"] = names
        (ROOT / "data" / "recipes.raw.json").write_text(
            json.dumps(raw, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"LLM-extracted ingredients for {len(todo)} recipes (cached in recipes.raw.json)")
    out = []
    for r in raw:
        ingredients = r.get("ingredients") or extract_all(r["ingredient_lines"])
        out.append({**r, "source": SOURCE, "ingredients": ingredients})
    (ROOT / "data" / "recipes.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {len(out)} recipes -> data/recipes.json")


if __name__ == "__main__":
    main()
