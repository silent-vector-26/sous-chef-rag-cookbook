# Contributing

Thanks for your interest! This is a demo project, but improvements are welcome.

## Setup
```powershell
pip install -e ".[ui,dev]"
python -m ingest.build_dataset
pytest
python -m eval.run_eval
```
The default `BACKEND=local` needs no Azure resources.

## Guidelines
- Open an issue before large changes.
- Keep `pytest` and `python -m eval.run_eval` passing; add tests for new behavior.
- Update `docs/SRS.md` (requirements, diagrams, traceability) and the relevant `cookbook/` recipe when behavior changes.
- Never commit secrets or `.env`; auth uses Entra ID / managed identity.
- Only add recipe data you have the right to redistribute (original wording or public domain).

## Pull requests
Branch from `main`, keep PRs focused, and describe what changed and how you verified it. CI must be green.
