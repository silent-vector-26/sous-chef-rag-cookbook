# 08 · Evaluation

**Serves:** 1 · **Difficulty:** ★★☆ · **Code:** `eval/run_eval.py`, `eval/golden.json`

## Method
1. Golden set: answerable questions (expected recipe id), unanswerable questions (must refuse), and pantry cases (expected top recipe + missing count).
2. Metrics: `retrieval_recall@5`, `retrieval_mrr`, `citation_accuracy`, `refusal_rate_on_unanswerable`, `pantry_top1_accuracy`, `pantry_missing_count_correct`, `pantry_sorted_by_missing`.
3. Run per backend and compare `eval/results/*.json` — chunking, hybrid vs keyword, reranker on/off.
4. For LLM-judged **groundedness/relevance**, add Azure AI Foundry evaluators (`azure-ai-evaluation`) over the same cases.

## Taste test
```
python -m eval.run_eval                  # BACKEND=local baseline
BACKEND=azure python -m eval.run_eval    # hybrid + semantic
```

## Chef's notes
Change one thing at a time and keep the table in the README. A tiny golden set that you actually run beats a big one you don't.
