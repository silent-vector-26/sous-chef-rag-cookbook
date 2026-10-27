"""Agentic RAG: the model decides which retrieval tool to call (and may call several times).

Implemented with Azure OpenAI tool calling; the same tool definitions can be registered with
Azure AI Foundry Agent Service (see cookbook/07-agentic-rag.md).
"""
import json

from . import llm
from .rag import cook_with
from .store import Store

TOOLS = [
    {"type": "function", "function": {
        "name": "search_recipes",
        "description": "Semantic/keyword search over cookbook recipes (techniques, dishes, how-to).",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "find_by_ingredients",
        "description": "Find recipes cookable from a list of ingredients the user has, ranked by fewest missing.",
        "parameters": {"type": "object", "properties": {
            "ingredients": {"type": "array", "items": {"type": "string"}},
            "max_missing": {"type": "integer"}}, "required": ["ingredients"]}}},
]

SYSTEM = ("You are Sous-chef, a cooking research agent. Use tools to ground every answer; compare options "
          "when useful; cite recipe ids like [r001]; say you don't know if tools return nothing relevant.")


def _run_tool(store: Store, name: str, args: dict) -> str:
    if name == "search_recipes":
        hits = store.search(args["query"], top=4)
        return json.dumps([{"id": r.id, "title": r.title, "text": r.text, "ingredients": r.ingredients}
                           for r, _ in hits])
    if name == "find_by_ingredients":
        res = cook_with("", store, max_missing=args.get("max_missing"), have=args["ingredients"], limit=5)
        return json.dumps([{"id": m.recipe.id, "title": m.recipe.title, "have": m.have, "missing": m.missing}
                           for m in res.matches])
    return "[]"


def run_agent(question: str, store: Store, max_steps: int = 5) -> tuple[str, list[str]]:
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    trace: list[str] = []
    client = llm._aoai()
    from . import config

    for _ in range(max_steps):
        r = client.chat.completions.create(
            model=config.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-5.4-mini"),
            messages=messages, tools=TOOLS)
        msg = r.choices[0].message
        if not msg.tool_calls:
            return msg.content or "", trace
        messages.append(msg)
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            trace.append(f"{call.function.name}({args})")
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": _run_tool(store, call.function.name, args)})
    return "I couldn't finish researching that within the step limit.", trace
