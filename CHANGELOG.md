# Changelog

## Unreleased
### Documentation
- Refreshed README navigation, build/deployment badges, setup instructions and current UI screenshots.
- Expanded the portfolio write-up with the recipe-tile design, offline-generated images and engineering trade-offs.
- Clarified evaluation methodology, safety/dietary scope, cost estimates and demo limitations.
- Fixed ingestion and evaluation Mermaid labels in both SDD and SRS.

## [0.1.0] - 2026-10-27
### Added
- Ingredient search ranked by fewest missing ingredients, shopping list and unlock tips
- Grounded Q&A with citations and refusal
- Azure AI Search hybrid + semantic store, offline local store
- Multimodal fridge-photo input, tool-calling agent, input safety checks
- Evaluation harness, SRS with Mermaid diagrams, cookbook recipes
- Bicep/azd infrastructure, Dockerfile, CI
- Editorial cookbook UI with pantry chips, image tiles and inline expandable recipe details
- 205 bundled AI-generated WebP food images
- GitHub OIDC deployment, custom OpenTelemetry spans and optional budget alerts
### Fixed
- Featured gallery no longer relies on the local-only `recipes` attribute; local and Azure UI regression tests cover initial load and filter reruns
