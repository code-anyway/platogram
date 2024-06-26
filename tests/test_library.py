import json

from pathlib import Path
from platogram.library import get_local
from platogram.types import Content


def test_library(tmp_path: Path) -> None:
    lib = get_local(tmp_path)

    with open("samples/jfk.json", "r") as file:
        indexed_doc = Content(**json.load(file))

    url = "https://en.wikipedia.org/wiki/Inauguration_of_John_F._Kennedy"
    lib.put(url, indexed_doc)

    query = "What does he say about the Vietnam war?"
    context = lib.retrieve(query, filter_keys=[url], n_results=16)

    assert len(context) == 16
