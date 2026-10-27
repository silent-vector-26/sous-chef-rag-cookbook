"""Sous-chef UI.   streamlit run app/streamlit_app.py"""
import base64
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from ragcookbook import config, llm  # noqa: E402
from ragcookbook.agent import run_agent  # noqa: E402
from ragcookbook.rag import ask, cook_with  # noqa: E402
from ragcookbook.store import get_store  # noqa: E402

IMG_DIR = Path(__file__).parent / "static" / "img"
PANTRY = ["chicken", "potatoes", "carrots", "rice", "eggs", "tomatoes", "onion", "garlic",
          "pasta", "spinach", "mushrooms", "beans", "cheese", "lemon"]
CSS = """
<style>
:root { --cream:#f4ede0; --ink:#2b2118; --accent:#b4472b; --green:#2f7d4f; }
.stApp { background: var(--cream); color: var(--ink); }
h1, h2, h3, .serif { font-family: Georgia, 'Times New Roman', serif !important; color: var(--ink); }
.hero { padding: 1.2rem 0 .6rem; border-bottom: 2px solid var(--ink); margin-bottom: 1rem; }
.hero h1 { font-size: 3rem; margin: 0; letter-spacing: -.5px; }
.hero p { font-family: Trebuchet MS, sans-serif; color: #6b5a4a; margin: .3rem 0 0; }
.card { display: flex; gap: 1rem; background: #fffaf1; border: 1px solid #d9ccb5;
        border-radius: 10px; overflow: hidden; margin-bottom: .8rem; }
.card .ph { width: 150px; min-height: 130px; flex: none; background-size: cover;
            background-position: center; display: flex; align-items: center;
            justify-content: center; font-size: 2.6rem; }
.card .body { padding: .7rem .9rem .7rem 0; }
.card h3 { margin: 0 0 .3rem; font-size: 1.3rem; }
.badge { display: inline-block; padding: .1rem .55rem; border-radius: 99px; font-size: .8rem;
         font-family: Trebuchet MS, sans-serif; margin-right: .4rem; }
.ok { background: #dcefe3; color: var(--green); }
.need { background: #f6dfd6; color: var(--accent); }
.meta { font-family: Trebuchet MS, sans-serif; font-size: .85rem; color: #6b5a4a; }
.stButton > button[kind="primary"] { background: var(--accent); border: 0; }
</style>
"""
FALLBACKS = [
    (("chicken", "turkey"), "#f0d6b8", "🍗"), (("beef", "steak", "pork", "lamb"), "#e9c9a0", "🥩"),
    (("fish", "salmon", "shrimp", "tuna", "cod"), "#d3e3ea", "🐟"), (("pasta", "spaghetti", "noodle"), "#f0d6b8", "🍝"),
    (("soup", "stew", "chili"), "#e9c9a0", "🍲"), (("salad", "veggie", "vegetable", "spinach"), "#cfe2c4", "🥗"),
    (("rice", "curry"), "#e4d3e8", "🍛"), (("egg", "omelet"), "#f6e6a8", "🍳"),
]


def _photo_style(recipe) -> tuple[str, str]:
    """Generated image if one exists, otherwise a tinted emoji tile."""
    for ext in ("webp", "jpg", "png"):
        f = IMG_DIR / f"{recipe.id}.{ext}"
        if f.exists():
            b64 = base64.b64encode(f.read_bytes()).decode()
            return f"background-image:url(data:image/{ext};base64,{b64})", ""
    title = recipe.title.lower()
    for words, color, emoji in FALLBACKS:
        if any(w in title for w in words):
            return f"background:{color}", emoji
    return "background:#e9dfc9", "🍽️"


def _card(m, total: int) -> str:
    style, emoji = _photo_style(m.recipe)
    miss = len(m.missing)
    badge = ('<span class="badge ok">cook it now</span>' if not miss
             else f'<span class="badge need">missing {miss}</span>')
    return (
        f'<div class="card"><div class="ph" style="{style}">{emoji}</div><div class="body">'
        f"<h3>{html.escape(m.recipe.title)}</h3>{badge}"
        f'<span class="meta">you have {len(m.have)}/{total}</span></div></div>'
    )


st.set_page_config(page_title="Sous-chef · RAG Cookbook", page_icon="🍳", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
store = st.cache_resource(get_store)()
azure = config.backend() == "azure"

st.markdown(
    '<div class="hero"><h1>Sous-chef</h1>'
    f"<p>Cook with what you have · backend: <b>{config.backend()}</b> · "
    "every answer is grounded in the cookbook and cited</p></div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    diet = st.multiselect("Dietary filters", ["vegetarian", "vegan", "gluten-free", "dairy-free"])
    max_missing = st.slider("Max missing ingredients", 0, 6, 3)

tab_cook, tab_ask, tab_agent = st.tabs(["🥕 Cook with what I have", "💬 Ask the cookbook", "🧭 Research agent"])

with tab_cook:
    st.markdown("##### Tap what's in your pantry")
    picked = st.pills("Pantry", PANTRY, selection_mode="multi", label_visibility="collapsed")
    extra = st.text_input("…or describe it", "", placeholder="e.g. leftover roast chicken and some leeks")
    photo = st.file_uploader("…or upload a fridge photo", type=["jpg", "jpeg", "png"]) if azure else None
    if st.button("Find recipes", type="primary"):
        if not (picked or extra or photo):
            st.warning("Pick at least one ingredient first.")
            st.stop()
        msg = "I have " + ", ".join([*(picked or []), *([extra] if extra else [])])
        have = llm.describe_image_ingredients(photo.getvalue(), photo.type) if photo else None
        res = cook_with(msg, store, max_missing=max_missing, diet=diet, have=have)
        st.markdown(f"**You have:** {', '.join(res.have) or '—'}")
        if not res.matches:
            st.info("Nothing close enough. Try raising the missing-ingredients limit.")
        for m in res.matches:
            total = len(m.have) + len(m.missing)
            st.markdown(_card(m, total), unsafe_allow_html=True)
            with st.expander("Recipe", expanded=m is res.matches[0]):
                st.progress(m.coverage)
                st.markdown("✅ " + ", ".join(m.have))
                st.markdown("🛒 Need: " + (", ".join(m.missing) or "nothing — cook it now!"))
                st.write(m.recipe.text)
                st.caption(f"{m.recipe.source}, p.{m.recipe.page}")
        if res.shopping:
            st.subheader("Shopping list")
            st.write(", ".join(res.shopping))
        for item, n in res.unlocks:
            st.success(f"Buy **{item}** and {n} more recipe(s) become fully cookable.")

with tab_ask:
    q = st.chat_input("Ask about a recipe or technique…")
    if q:
        st.chat_message("user").write(q)
        ans = ask(q, store, diet=diet)
        with st.chat_message("assistant"):
            st.write(ans.text)
            for c in ans.citations:
                st.caption(f"📖 [{c.id}] {c.title} — {c.source}, p.{c.page}")

with tab_agent:
    if not azure:
        st.info("The research agent needs BACKEND=azure (Azure OpenAI tool calling).")
    else:
        aq = st.text_input("Complex question", "Compare my options for dinner with chicken and carrots, vegetarian sides included")
        if st.button("Run agent"):
            answer, trace = run_agent(aq, store)
            st.write(answer)
            with st.expander("Tool calls"):
                st.code("\n".join(trace) or "(none)")
