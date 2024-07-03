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
        filter_keys: list[str] = [],
    ) -> list[Content]: ...

    def get_content(self, id: str) -> Content: ...


def get_local(home_dir: Path = Path("./my_library")) -> Library:
    from .local import LocalLibrary

    return LocalLibrary(home_dir)
