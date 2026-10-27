# Security Policy

## Reporting a vulnerability
Please use GitHub's **Private vulnerability reporting** (Security tab → Report a vulnerability). Do not open public issues for security problems.

## Design notes
- No API keys: Azure OpenAI, AI Search and Content Safety use Entra ID / managed identity (`disableLocalAuth: true`).
- Q&A and pantry-text parsing use Prompt Shields / Content Safety when an endpoint is configured; otherwise they use a heuristic. The agent's top-level prompt/direct search tool and image extraction do not all share that gate.
- Never commit `.env` or credentials.

This is a public demonstration, not a hardened production service. Recipe tags, generated text and image detections are not suitable for allergy, nutrition or medical decisions. See [SDD security design](docs/SDD.md#7-security-design) for identity and guardrail scope.
