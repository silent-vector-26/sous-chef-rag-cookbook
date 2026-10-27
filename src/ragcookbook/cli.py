"""Command-line entry point.

    python -m ragcookbook.cli cook "I have chicken, potatoes and carrots"
    python -m ragcookbook.cli ask "How long do I roast a chicken?"
"""
import argparse

from .rag import ask, cook_with
from .store import get_store


def main() -> None:
    ap = argparse.ArgumentParser(prog="sous-chef")
    ap.add_argument("mode", choices=["cook", "ask"])
    ap.add_argument("text")
    ap.add_argument("--max-missing", type=int)
    ap.add_argument("--diet", action="append", default=[])
    a = ap.parse_args()
    store = get_store()

    if a.mode == "ask":
        ans = ask(a.text, store, diet=a.diet)
        print(ans.text)
        for c in ans.citations:
            print(f"  - [{c.id}] {c.title} — {c.source}, p.{c.page}")
        return

    res = cook_with(a.text, store, max_missing=a.max_missing, diet=a.diet)
    print(f"You have: {', '.join(res.have) or '(nothing recognised)'}\n")
    for m in res.matches:
        total = len(m.have) + len(m.missing)
        print(f"{m.recipe.title}  [{len(m.have)}/{total}]  missing: {', '.join(m.missing) or 'nothing!'}")
    if res.shopping:
        print(f"\nShopping list: {', '.join(res.shopping)}")
    for item, n in res.unlocks:
        print(f"Tip: buying {item} makes {n} more recipe(s) fully cookable")


if __name__ == "__main__":
    main()
