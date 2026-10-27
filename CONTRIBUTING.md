# Contributing

Sous-chef is an AI engineering demo with a deterministic core and optional Azure integrations. Focused bug fixes, tests and documentation improvements are welcome.

## Setup
Use Python 3.10+ and a virtual environment. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[ui,dev]"
$env:BACKEND = "local"
python -m ingest.build_dataset
python -m pytest -q
python -m eval.run_eval
```
`BACKEND=local` needs no Azure resources. Installing the `ui` extra ensures the Streamlit regression tests run rather than being skipped. See [README](README.md#run-on-azure) for cloud-backed development.

## Guidelines
- Open an issue before large changes.
- Run `python -m pytest -q` and `python -m eval.run_eval`; add regression tests for changed behavior. The evaluator reports metrics but does not enforce thresholds, so review the values rather than just the exit code.
- Exercise UI changes against both backend interfaces. Do not rely on implementation-specific attributes such as `LocalStore.recipes` in shared UI paths.
- Update `docs/SRS.md` (requirements, diagrams, traceability) and the relevant `cookbook/` recipe when behavior changes.
- Never commit secrets or `.env`; auth uses Entra ID / managed identity.
- Only add recipe data you have the right to redistribute (original wording or public domain).
- Label generated images and synthetic data; do not present them as validated cooking or dietary advice.

## Pull requests
Branch from `main`, keep PRs focused, and describe what changed and how you verified it. CI must be green.

Use the [PR template](.github/PULL_REQUEST_TEMPLATE.md), listing exact commands and their outcomes. Mark checks that were not run explicitly. CI runs tests, local evaluation and a Bicep build. Deployment starts automatically after successful push-triggered CI on `main`; its HTTP smoke test is not a substitute for checking interactive workflows.

For visual changes, update the relevant files in `docs/img/` using the current UI. Use synthetic fixtures, never private fridge photos or personal data. For Mermaid changes, quote labels containing special characters (for example `["Recall@5, MRR"]`), validate rendering, and keep repeated SRS/SDD diagrams consistent.
