# Security Policy

## Reporting a vulnerability
Please use GitHub's **Private vulnerability reporting** (Security tab → Report a vulnerability). Do not open public issues for security problems.

## Design notes
- No API keys: Azure OpenAI, AI Search and Content Safety use Entra ID / managed identity (`disableLocalAuth: true`).
- User input is screened (Prompt Shields / Content Safety) before retrieval.
- Never commit `.env` or credentials.
