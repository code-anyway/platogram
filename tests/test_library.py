import json

from pathlib import Path
from platogram.library import get_semantic_local_chroma, get_keyword_local_bm25
from platogram.types import Content
from platogram.utils import make_filesystem_safe


def test_semantic_local_chroma(tmp_path: Path) -> None:
    lib = get_semantic_local_chroma(tmp_path)

    with open("samples/jfk.json", "r") as file:
        indexed_doc = Content(**json.load(file))

    url = "https://en.wikipedia.org/wiki/Inauguration_of_John_F._Kennedy"
    id = make_filesystem_safe(url)
    lib.put(id, indexed_doc)

    query = "What does he say about the Vietnam war?"
    context, distances = lib.retrieve(query, filter_keys=[id], n_results=16)

    assert len(context) == 1
    assert len(distances) == 16
    assert len(context[0].passages) == len(distances)


def test_keyword_local_bm25(tmp_path: Path) -> None:
    lib = get_keyword_local_bm25(tmp_path)

    with open("samples/jfk.json", "r") as file:
        indexed_doc = Content(**json.load(file))

    url = "https://en.wikipedia.org/wiki/Inauguration_of_John_F._Kennedy"
    id = make_filesystem_safe(url)
    lib.put(id, indexed_doc)

    query = "United Nations"
    context, distances = lib.retrieve(query, filter_keys=[id], n_results=16)

    assert len(context) == 1
    assert len(distances) == 16
    assert len(context[0].passages) == len(distances)
    assert "United Nations" in context[0].passages[0]
