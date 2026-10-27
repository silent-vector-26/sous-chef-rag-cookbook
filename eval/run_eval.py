"""Evaluate retrieval, grounding/refusal and pantry ranking against eval/golden.json.

    python -m eval.run_eval            # uses BACKEND from .env (local or azure)
Writes eval/results/<backend>.json so you can compare strategies side by side.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ragcookbook import config  # noqa: E402
from ragcookbook.rag import ask, cook_with  # noqa: E402
from ragcookbook.store import get_store  # noqa: E402


def main() -> None:
    golden = json.loads((ROOT / "eval" / "golden.json").read_text(encoding="utf-8"))
    store = get_store()

    answerable = [g for g in golden["qa"] if g["expect_id"]]
    unanswerable = [g for g in golden["qa"] if not g["expect_id"]]

    hit = rr = 0.0
    for g in answerable:
        ids = [r.id for r, _ in store.search(g["q"], top=5)]
        if g["expect_id"] in ids:
            hit += 1
            rr += 1 / (ids.index(g["expect_id"]) + 1)
    cited = sum(1 for g in answerable if any(c.id == g["expect_id"] for c in ask(g["q"], store).citations))
    refused = sum(1 for g in unanswerable if not ask(g["q"], store).grounded)

    top1 = missing_ok = ordered = 0
    for g in golden["pantry"]:
        res = cook_with(g["q"], store)
        if res.matches and res.matches[0].recipe.id == g["expect_top"]:
            top1 += 1
            if len(res.matches[0].missing) == g["expect_top_missing"]:
                missing_ok += 1
        counts = [len(m.missing) for m in res.matches]
        ordered += counts == sorted(counts)

    n, p = len(answerable), len(golden["pantry"])
    metrics = {
        "backend": config.backend(),
        "retrieval_recall@5": hit / n,
        "retrieval_mrr": rr / n,
        "citation_accuracy": cited / n,
        "refusal_rate_on_unanswerable": refused / len(unanswerable),
        "pantry_top1_accuracy": top1 / p,
        "pantry_missing_count_correct": missing_ok / p,
        "pantry_sorted_by_missing": ordered / p,
    }
    out = ROOT / "eval" / "results"
    out.mkdir(exist_ok=True)
    (out / f"{metrics['backend']}.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("| metric | value |\n|---|---|")
    for k, v in metrics.items():
        print(f"| {k} | {v:.2f} |" if isinstance(v, float) else f"| {k} | {v} |")


if __name__ == "__main__":
    main()
