import json
from pathlib import Path

try:
    import bm25s  # type: ignore
except ImportError:
    pass

try:
    import Stemmer  # type: ignore
except ImportError:
    pass

from platogram.types import Content
from platogram.utils import make_filesystem_safe
from platogram.ops import remove_markers


class LocalBM25Library:
    def __init__(self, home_dir: Path):
        if not home_dir.exists():
            home_dir.mkdir(parents=True)
        self.home_dir = home_dir
        self.stemmer = Stemmer.Stemmer("english")

    @property
    def home(self) -> Path:
        return self.home_dir

    def ls(self) -> list[str]:
        return [f.stem for f in self.home.glob("*.json")]

    def exists(self, id: str) -> bool:
        return (self.home / f"{make_filesystem_safe(id)}.json").exists()

    def put(self, id: str, content: Content) -> None:
        file = self.home / f"{make_filesystem_safe(id)}.json"
        with open(file, "w") as f:
            json.dump(content.model_dump(mode="json"), f)

        self.passage_retriever = bm25s.BM25()
        passages_tokens = bm25s.tokenize(
            [remove_markers(passage) for passage in content.passages],
            stopwords="en",
            stemmer=self.stemmer,
        )
        self.passage_retriever.index(passages_tokens)

    def get_content(self, id: str) -> Content:
        file = self.home_dir / f"{make_filesystem_safe(id)}.json"
        with open(file, "r") as f:
            content = Content(**json.load(f))
        return content

    def delete(self, id: str) -> None:
        file = self.home_dir / f"{make_filesystem_safe(id)}.json"
        file.unlink()

    def retrieve(
        self,
        query: str,
        n_results: int,
        filter_keys: list[str],
    ) -> tuple[list[Content], list[float]]:
        if len(filter_keys) == 0:
            return ([], [])

        if len(filter_keys) > 1:
            raise ValueError(
                "Keyword local BM25 library cannot handle multiple documents"
            )

        content = self.get_content(filter_keys[0])
        n_passages = min(len(content.passages), n_results)

        query_tokens = bm25s.tokenize(query, stemmer=self.stemmer)
        ids, distances = self.passage_retriever.retrieve(query_tokens, k=n_passages)  # type: ignore

        content.passages = [content.passages[i] for i in ids[0]]

        return ([content], distances[0])
