from pathlib import Path
from unittest.mock import Mock

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

from ragcookbook import config, store


@pytest.mark.parametrize("backend", ["local", "azure"])
def test_featured_gallery_does_not_depend_on_store_recipes(monkeypatch, backend):
    retrieval_store = Mock(spec=store.Store)
    monkeypatch.setattr(config, "backend", lambda: backend)
    monkeypatch.setattr(store, "get_store", lambda: retrieval_store)

    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")
    ).run()

    assert not app.exception
    gallery = next(m.value for m in app.markdown if '<div class="grid">' in m.value)
    assert gallery.count('class="tile"') == 8
    retrieval_store.search.assert_not_called()
    retrieval_store.candidates_by_ingredients.assert_not_called()

    app.multiselect[0].select("vegetarian").run()
    assert not app.exception
    assert any("From the cookbook" in m.value for m in app.markdown)
