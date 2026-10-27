# 08 · Evaluation

**Serves:** 1 · **Difficulty:** ★★☆ · **Code:** `eval/run_eval.py`, `eval/golden.json`

## Method
1. Golden set: answerable questions (expected recipe id), unanswerable questions (must refuse), and pantry cases (expected top recipe + missing count).
2. Metrics: `retrieval_recall@5`, `retrieval_mrr`, `citation_accuracy`, `refusal_rate_on_unanswerable`, `pantry_top1_accuracy`, `pantry_missing_count_correct`, `pantry_sorted_by_missing`.
3. Run per backend and compare `eval/results/*.json`. Local TF-IDF and Azure hybrid/semantic are the implemented backends; chunking and reranker ablations require explicit code/configuration changes, not an existing evaluator switch.
4. For LLM-judged **groundedness/relevance**, add Azure AI Foundry evaluators (`azure-ai-evaluation`) over the same cases.

## Taste test
```powershell
$env:BACKEND = "local"
python -m eval.run_eval
$env:BACKEND = "azure"                   # configured endpoints + Entra ID required
python -m eval.run_eval
```

## Chef's notes
The current golden set has 13 answerable questions, seven expected refusals and five pantry cases. The corpus contains 205 demo recipes (180 LLM-generated), so results should not be generalized to unseen cookbooks.

`citation_accuracy` is the fraction of answerable cases whose expected recipe appears in the returned citation list. It is an expected-source hit rate, not claim-level factual accuracy. The answer path can fall back to citing the top retrieved recipe when no recognized source tag is present.

`pantry_missing_count_correct` counts cases where both the top recipe and its missing count match expectations. `pantry_sorted_by_missing` checks ascending counts and also counts an empty result list as sorted; it must be read alongside top-1 accuracy.

The evaluator exits successfully after computing metrics; it does not currently enforce quality thresholds. Local extractive answers are a development baseline, not a proxy for live LLM quality. Change one thing at a time, retain results outside version control, and distinguish historical Azure measurements from current smoke checks.
