from pathlib import Path
from typing import Protocol

from platogram.types import Content


class Library(Protocol):
    @property
    def home(self) -> Path: ...

    def ls(self) -> list[str]: ...

    def exists(self, id: str) -> bool: ...

    def put(self, id: str, content: Content): ...

    def retrieve(
        self,
        query: str,
        n_results: int,
        filter_keys: list[str],
    ) -> tuple[list[Content], list[float]]: ...

    def get_content(self, id: str) -> Content: ...


def get_semantic_local_chroma(home_dir: Path = Path("./my_library")) -> Library:
    from .semantic_local_chroma import LocalChromaLibrary

    return LocalChromaLibrary(home_dir)


def get_keyword_local_bm25(home_dir: Path = Path("./my_library")) -> Library:
    from .keyword_local_bm25 import LocalBM25Library

    return LocalBM25Library(home_dir)


def get_local_dumb(home_dir: Path = Path("./my_library")) -> Library:
    from .local_dumb import LocalDumbLibrary

    return LocalDumbLibrary(home_dir)