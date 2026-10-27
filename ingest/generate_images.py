"""One-time offline generation of recipe images (AI-generated, labelled as such).

  python ingest/generate_images.py [--limit N]

Needs the temporary `img-mini` deployment (gpt-image-1-mini) and `az login`.
Output: app/static/img/<recipe id>.webp (~512px). Existing files are skipped.
"""
import argparse
import base64
import io
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image  # noqa: E402

from ragcookbook import llm  # noqa: E402

OUT = ROOT / "app" / "static" / "img"
DEPLOYMENT = "img-mini"
PROMPT = ("Appetizing overhead food photograph of {title}, plated on a rustic ceramic dish, "
          "natural window light, warm tones, shallow depth of field, no text, no people")


def generate(recipe: dict) -> str:
    dest = OUT / f"{recipe['id']}.webp"
    if dest.exists():
        return "skip"
    for attempt in range(4):
        try:
            res = llm._aoai().images.generate(
                model=DEPLOYMENT, prompt=PROMPT.format(title=recipe["title"]),
                size="1024x1024", quality="low", n=1)
            img = Image.open(io.BytesIO(base64.b64decode(res.data[0].b64_json))).convert("RGB")
            img.resize((512, 512)).save(dest, "WEBP", quality=70)
            return "ok"
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                return f"fail: {e}"
            import time
            time.sleep(5 * (attempt + 1))
    return "fail"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    recipes = json.loads((ROOT / "data" / "recipes.json").read_text(encoding="utf-8"))[: args.limit]
    with ThreadPoolExecutor(3) as ex:
        results = list(ex.map(generate, recipes))
    print({k: results.count(k) for k in {r.split(":")[0] for r in results}})
    print([r for r in results if r.startswith("fail")][:3])
