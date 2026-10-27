"""Input guardrails: prompt-injection detection + content safety.

Azure mode uses Azure AI Content Safety (Prompt Shields + harm categories).
Local mode uses a small heuristic so the demo still shows the control point.
"""
import json
import re
import urllib.request
from dataclasses import dataclass

from . import config

_INJECTION = re.compile(
    r"ignore (all |any )?(previous|prior|above) (instructions|rules)|reveal (your )?(system )?prompt|"
    r"disregard .* (instructions|rules)|you are now|developer mode|jailbreak", re.I)


@dataclass
class SafetyResult:
    allowed: bool
    reason: str = ""


def check_input(text: str) -> SafetyResult:
    endpoint = config.get("AZURE_CONTENT_SAFETY_ENDPOINT")
    if config.backend() != "azure" or not endpoint:
        if _INJECTION.search(text):
            return SafetyResult(False, "Possible prompt injection detected")
        return SafetyResult(True)

    from azure.identity import DefaultAzureCredential

    token = DefaultAzureCredential().get_token("https://cognitiveservices.azure.com/.default").token
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def post(path: str, body: dict) -> dict:
        req = urllib.request.Request(f"{endpoint.rstrip('/')}{path}", json.dumps(body).encode(), headers)
        with urllib.request.urlopen(req, timeout=15) as r:  # noqa: S310 (fixed https endpoint from config)
            return json.loads(r.read())

    shield = post("/contentsafety/text:shieldPrompt?api-version=2024-09-01",
                  {"userPrompt": text, "documents": []})
    if shield.get("userPromptAnalysis", {}).get("attackDetected"):
        return SafetyResult(False, "Prompt Shields flagged a jailbreak attempt")
    harm = post("/contentsafety/text:analyze?api-version=2024-09-01", {"text": text})
    for cat in harm.get("categoriesAnalysis", []):
        if cat.get("severity", 0) >= 4:
            return SafetyResult(False, f"Content Safety blocked category: {cat.get('category')}")
    return SafetyResult(True)
