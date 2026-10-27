"""Sous-chef UI.   streamlit run app/streamlit_app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from ragcookbook import config, llm  # noqa: E402
from ragcookbook.agent import run_agent  # noqa: E402
from ragcookbook.rag import ask, cook_with  # noqa: E402
from ragcookbook.store import get_store  # noqa: E402

st.set_page_config(page_title="Sous-chef · RAG Cookbook", page_icon="🍳", layout="wide")
store = st.cache_resource(get_store)()
azure = config.backend() == "azure"

st.title("🍳 Sous-chef — RAG Cookbook")
st.caption(f"Backend: **{config.backend()}** · answers are grounded in the cookbook and cited")

with st.sidebar:
    diet = st.multiselect("Dietary filters", ["vegetarian", "vegan", "gluten-free", "dairy-free"])
    max_missing = st.slider("Max missing ingredients", 0, 6, 3)

tab_cook, tab_ask, tab_agent = st.tabs(["🥕 Cook with what I have", "💬 Ask the cookbook", "🧭 Research agent"])

with tab_cook:
    msg = st.text_input("What's in your kitchen?", "I have chicken, potatoes and carrots")
    photo = st.file_uploader("…or upload a fridge photo", type=["jpg", "jpeg", "png"]) if azure else None
    if st.button("Find recipes", type="primary"):
        have = llm.describe_image_ingredients(photo.getvalue(), photo.type) if photo else None
        res = cook_with(msg, store, max_missing=max_missing, diet=diet, have=have)
        st.write("**You have:**", ", ".join(res.have) or "—")
        if not res.matches:
            st.info("Nothing close enough. Try raising the missing-ingredients limit.")
        for m in res.matches:
            total = len(m.have) + len(m.missing)
            with st.expander(f"{m.recipe.title} — you have {len(m.have)}/{total}", expanded=m is res.matches[0]):
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
