import json
from pathlib import Path

from platogram.types import Content
from platogram.utils import make_filesystem_safe


class LocalDumbLibrary:
    def __init__(self, home_dir: Path):
        if not home_dir.exists():
            home_dir.mkdir(parents=True)
        self.home_dir = home_dir

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
        raise NotImplementedError("Dumb local storage does not support retrieval. Use get_content().")
