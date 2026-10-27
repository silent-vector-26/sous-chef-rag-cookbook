"""Sous-chef UI.   streamlit run app/streamlit_app.py"""
import base64
import html
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from ragcookbook import config, llm  # noqa: E402
from ragcookbook.agent import run_agent  # noqa: E402
from ragcookbook.rag import ask, cook_with  # noqa: E402
from ragcookbook.store import get_store, load_recipes  # noqa: E402

IMG_DIR = Path(__file__).parent / "static" / "img"
PANTRY = ["chicken", "potatoes", "carrots", "rice", "eggs", "tomatoes", "onion", "garlic",
          "pasta", "spinach", "mushrooms", "beans", "cheese", "lemon"]
HERO_IDS = ["r001", "r012", "r040", "r075", "r110", "r150"]
CSS = """
<style>
header[data-testid="stHeader"], footer, #MainMenu { display: none; }
.block-container { max-width: 1180px; padding-top: 1.2rem; }
h1, h2, h3, h4, .serif { font-family: Georgia, 'Times New Roman', serif !important; letter-spacing: -.3px; }
.sans, .badge, .meta, .eyebrow, label, .stTabs button { font-family: 'Trebuchet MS', sans-serif !important; }
.masthead { display: flex; justify-content: space-between; align-items: baseline;
            border-bottom: 3px double #2b2118; padding-bottom: .5rem; margin-bottom: 1rem; }
.masthead b { font: 700 1.5rem Georgia, serif; }
.masthead span { font: .8rem 'Trebuchet MS', sans-serif; color: #6b5a4a; text-transform: uppercase; letter-spacing: 2px; }
.hero { position: relative; border-radius: 14px; overflow: hidden; margin-bottom: 1.4rem; }
.mosaic { display: grid; grid-template-columns: repeat(6, 1fr); height: 280px; }
.mosaic div { background-size: cover; background-position: center; }
.hero .veil { position: absolute; inset: 0; background: linear-gradient(90deg, rgba(43,33,24,.88) 30%, rgba(43,33,24,.15)); }
.hero .copy { position: absolute; left: 2.2rem; top: 50%; transform: translateY(-50%); color: #fffaf1; max-width: 560px; }
.hero .eyebrow { text-transform: uppercase; letter-spacing: 3px; font-size: .75rem; color: #f2b134; }
.hero h1 { color: #fffaf1; font-size: 3.4rem; line-height: 1.05; margin: .3rem 0 .6rem; }
.hero p { color: #eadfca; font-size: 1.05rem; margin: 0; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1.1rem; margin: .6rem 0 1.4rem; }
.tile { background: #fffaf1; border: 1px solid #d9ccb5; border-radius: 12px; overflow: hidden; }
.tile .ph { height: 190px; background-size: cover; background-position: center; display: flex;
            align-items: center; justify-content: center; font-size: 3.4rem; }
.tile .body { padding: .75rem .9rem .9rem; }
.tile h3 { font-size: 1.1rem; line-height: 1.25; margin: 0 0 .5rem; min-height: 2.7rem; }
.badge { display: inline-block; padding: .12rem .6rem; border-radius: 99px; font-size: .78rem; margin-right: .35rem; }
.ok { background: #dcefe3; color: #2f7d4f; }
.need { background: #f6dfd6; color: #b4472b; }
.meta { font-size: .82rem; color: #6b5a4a; }
.grid { align-items: start; }
.tile details { margin-top: .7rem; border-top: 1px solid #e6dac4; padding-top: .5rem; font-size: .92rem; }
.tile summary { cursor: pointer; font: 700 .85rem 'Trebuchet MS', sans-serif; color: #b4472b; }
.tile details p { margin: .45rem 0; }
.tile .steps { line-height: 1.5; }
.bar { height: 6px; background: #eadfca; border-radius: 9px; margin-top: .6rem; }
.bar i { display: block; height: 100%; background: #b4472b; border-radius: 9px; }
.sect { font: 700 1.6rem Georgia, serif; margin: 1rem 0 .1rem; }
.sect + .meta { margin-bottom: .6rem; }
.stButton > button[kind="primary"] { background: #2b2118; color: #fffaf1; border: 0; border-radius: 99px;
                                      padding: .55rem 1.6rem; font-family: 'Trebuchet MS', sans-serif; }
.stButton > button[kind="primary"]:hover { background: #b4472b; }
.stTabs [data-baseweb="tab-list"] { gap: 1.5rem; border-bottom: 1px solid #d9ccb5; }
.stTabs button[aria-selected="true"] { color: #b4472b; }
</style>
"""
FALLBACKS = [
    (("chicken", "turkey"), "#f0d6b8", "🍗"), (("beef", "steak", "pork", "lamb"), "#e9c9a0", "🥩"),
    (("fish", "salmon", "shrimp", "tuna", "cod"), "#d3e3ea", "🐟"), (("pasta", "spaghetti", "noodle"), "#f0d6b8", "🍝"),
    (("soup", "stew", "chili"), "#e9c9a0", "🍲"), (("salad", "veggie", "vegetable", "spinach"), "#cfe2c4", "🥗"),
    (("rice", "curry"), "#e4d3e8", "🍛"), (("egg", "omelet"), "#f6e6a8", "🍳"),
]


@lru_cache(maxsize=512)
def _data_uri(recipe_id: str) -> str | None:
    f = IMG_DIR / f"{recipe_id}.webp"
    if not f.exists():
        return None
    return "data:image/webp;base64," + base64.b64encode(f.read_bytes()).decode()


def _photo_style(recipe) -> tuple[str, str]:
    """Generated image if one exists, otherwise a tinted emoji tile."""
    uri = _data_uri(recipe.id)
    if uri:
        return f"background-image:url({uri})", ""
    title = recipe.title.lower()
    for words, color, emoji in FALLBACKS:
        if any(w in title for w in words):
            return f"background:{color}", emoji
    return "background:#e9dfc9", "🍽️"


def _tile(recipe, badges: str, detail: str = "") -> str:
    style, emoji = _photo_style(recipe)
    return (f'<div class="tile"><div class="ph" style="{style}">{emoji}</div><div class="body">'
            f"<h3>{html.escape(recipe.title)}</h3>{badges}{detail}</div></div>")


def _detail(m) -> str:
    e = html.escape
    need = e(", ".join(m.missing)) or "nothing — cook it now!"
    return ('<details><summary>View recipe</summary>'
            f'<div class="bar"><i style="width:{round(m.coverage * 100)}%"></i></div>'
            f'<p>✅ {e(", ".join(m.have))}</p><p>🛒 Need: {need}</p>'
            f'<p class="steps">{e(m.recipe.text)}</p>'
            f'<p class="meta">{e(str(m.recipe.source))}, p.{m.recipe.page}</p></details>')


def _hero() -> str:
    cells = "".join(f'<div style="background-image:url({u})"></div>' for i in HERO_IDS if (u := _data_uri(i)))
    mosaic = f'<div class="mosaic">{cells}</div>' if cells else '<div class="mosaic" style="background:#2b2118"></div>'
    return (f'<div class="hero">{mosaic}<div class="veil"></div><div class="copy">'
            '<div class="eyebrow sans">RAG cookbook · Azure AI Search + OpenAI</div>'
            "<h1>Cook with what you already have.</h1>"
            "<p>Tap your pantry. Get recipes ranked by fewest missing ingredients, "
            "every answer grounded in the cookbook and cited.</p></div></div>")


st.set_page_config(page_title="Sous-chef · RAG Cookbook", page_icon="🍳", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(CSS, unsafe_allow_html=True)
store = st.cache_resource(get_store)()
azure = config.backend() == "azure"

st.markdown(f'<div class="masthead"><b>Sous-chef</b><span>backend · {config.backend()}</span></div>',
            unsafe_allow_html=True)
st.markdown(_hero(), unsafe_allow_html=True)

f1, f2 = st.columns([3, 2])
diet = f1.multiselect("Dietary filters", ["vegetarian", "vegan", "gluten-free", "dairy-free"])
max_missing = f2.slider("Max missing ingredients", 0, 6, 3)

tab_cook, tab_ask, tab_agent = st.tabs(["🥕 Cook with what I have", "💬 Ask the cookbook", "🧭 Research agent"])

with tab_cook:
    st.markdown('<div class="sect">What\'s in your pantry?</div><div class="meta">Tap to add, '
                "or describe it below.</div>", unsafe_allow_html=True)
    picked = st.pills("Pantry", PANTRY, selection_mode="multi", label_visibility="collapsed")
    extra = st.text_input("…or describe it", "", placeholder="e.g. leftover roast chicken and some leeks")
    photo = st.file_uploader("…or upload a fridge photo", type=["jpg", "jpeg", "png"]) if azure else None
    go = st.button("Find recipes", type="primary")

    if go and not (picked or extra or photo):
        st.warning("Pick at least one ingredient first.")
    elif go:
        msg = "I have " + ", ".join([*(picked or []), *([extra] if extra else [])])
        have = llm.describe_image_ingredients(photo.getvalue(), photo.type) if photo else None
        res = cook_with(msg, store, max_missing=max_missing, diet=diet, have=have)
        st.markdown(f'<div class="sect">Tonight\'s menu</div><div class="meta">You have: '
                    f"{html.escape(', '.join(res.have) or '—')}</div>", unsafe_allow_html=True)
        if not res.matches:
            st.info("Nothing close enough. Try raising the missing-ingredients limit.")
        tiles = []
        for m in res.matches:
            total = len(m.have) + len(m.missing)
            badge = ('<span class="badge ok">cook it now</span>' if not m.missing
                     else f'<span class="badge need">missing {len(m.missing)}</span>')
            tiles.append(_tile(m.recipe, f'{badge}<span class="meta">you have {len(m.have)}/{total}</span>',
                               _detail(m)))
        st.markdown(f'<div class="grid">{"".join(tiles)}</div>', unsafe_allow_html=True)
        if res.shopping:
            st.subheader("Shopping list")
            st.write(", ".join(res.shopping))
        for item, n in res.unlocks:
            st.success(f"Buy **{item}** and {n} more recipe(s) become fully cookable.")
    else:
        feat = [r for r in st.cache_data(load_recipes)() if _data_uri(r.id)][6:14]
        st.markdown('<div class="sect">From the cookbook</div><div class="meta">A few to get you hungry.</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="grid">' + "".join(
            _tile(r, f'<span class="meta">{len(r.ingredients)} ingredients</span>') for r in feat) + "</div>",
            unsafe_allow_html=True)

with tab_ask:
    q = st.chat_input("Ask about a recipe or technique…")
    if q:
        st.chat_message("user").write(q)
        ans = ask(q, store, diet=diet)
        with st.chat_message("assistant"):
            st.write(ans.text)
            for c in ans.citations:
                st.caption(f"📖 [{c.id}] {c.title} — {c.source}, p.{c.page}")
    else:
        st.markdown('<div class="meta">Ask anything, e.g. “How do I roast a chicken?” '
                    "Answers cite their source or politely refuse.</div>", unsafe_allow_html=True)

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
