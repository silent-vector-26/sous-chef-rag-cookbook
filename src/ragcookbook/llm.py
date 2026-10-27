"""Azure OpenAI helpers with offline fallbacks (used when BACKEND=local)."""
import json

from . import config
from .ingredient_search import parse_pantry_heuristic
from .normalize import normalize_list

_client = None


def _aoai():
    global _client
    if _client is None:
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        from openai import AzureOpenAI

        _client = AzureOpenAI(
            azure_endpoint=config.get("AZURE_OPENAI_ENDPOINT"),
            azure_ad_token_provider=get_bearer_token_provider(
                DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"),
            api_version=config.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )
    return _client


def chat(messages: list[dict], json_mode: bool = False, temperature: float = 0.0) -> str:
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    r = _aoai().chat.completions.create(
        model=config.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini"),
        messages=messages, temperature=temperature, **kwargs)
    return r.choices[0].message.content or ""


def parse_pantry(message: str) -> list[str]:
    """'I have chicken, potatoes and 2 carrots' -> ['chicken','potato','carrot']."""
    if config.backend() != "azure":
        return parse_pantry_heuristic(message)
    out = chat([
        {"role": "system", "content": 'Extract the food ingredients the user says they have. '
         'Return JSON {"ingredients": ["singular lowercase names"]}. No quantities, no extras.'},
        {"role": "user", "content": message},
    ], json_mode=True)
    return normalize_list(json.loads(out).get("ingredients", []))


def extract_ingredients_llm(lines: list[str]) -> list[str]:
    out = chat([
        {"role": "system", "content": 'Convert recipe ingredient lines into canonical ingredient names: '
         'singular, lowercase, no quantities/units/prep words, "olive oil"->"oil". '
         'Return JSON {"ingredients": [...]}.'},
        {"role": "user", "content": "\n".join(lines)},
    ], json_mode=True)
    return normalize_list(json.loads(out).get("ingredients", []))


def describe_image_ingredients(image_bytes: bytes, mime: str = "image/jpeg") -> list[str]:
    """Multimodal: list the food ingredients visible in a fridge/pantry photo."""
    import base64

    b64 = base64.b64encode(image_bytes).decode()
    out = chat([
        {"role": "system", "content": 'List distinct edible ingredients visible in the photo. '
         'Return JSON {"ingredients": ["singular lowercase names"]}. Only what you can clearly see.'},
        {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}]},
    ], json_mode=True)
    return normalize_list(json.loads(out).get("ingredients", []))
