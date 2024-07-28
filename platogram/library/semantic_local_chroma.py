import json
import os
from pathlib import Path

try:
    import chromadb
except ImportError:
    pass

try:
    from chromadb.utils import embedding_functions
except ImportError:
    pass

from platogram.ops import remove_markers
from platogram.types import Content
from platogram.utils import get_sha256_hash, make_filesystem_safe

EMBEDDING_MODEL = "text-embedding-3-large"


class LocalChromaLibrary:
    def __init__(self, home_dir: Path):
        if not home_dir.exists():
            home_dir.mkdir(parents=True)
        self.home_dir = home_dir

        self.client = chromadb.PersistentClient(path=str(home_dir / "chroma.index"))

        embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.environ.get("OPENAI_API_KEY"), model_name=EMBEDDING_MODEL
        )
        self.content = self.client.get_or_create_collection(
            name="content",
            embedding_function=embedding_function,  # type: ignore
        )
        self.segments = self.client.get_or_create_collection(
            name="segments",
            embedding_function=embedding_function,  # type: ignore
        )

    @property
    def home(self) -> Path:
        return self.home_dir

    def ls(self) -> list[str]:
        return [f.stem for f in self.home.glob("*.json")]

    def exists(self, id: str) -> bool:
        return bool(self.content.get(ids=[id])["ids"])

    def put(self, id: str, content: Content) -> None:
        file = self.home / f"{make_filesystem_safe(id)}.json"
        with open(file, "w") as f:
            json.dump(content.model_dump(mode="json"), f)

        self.content.add(
            documents=[f"{content.title} {content.summary}"],
            ids=[id],
        )

        self.segments.add(
            documents=[remove_markers(p) for p in content.passages],
            metadatas=[{"id": id, "passage": p} for p in content.passages],
            ids=[get_sha256_hash(f"{id}-{p}") for p in content.passages],
        )

    def get_content(self, id: str) -> Content:
        file = self.home_dir / f"{make_filesystem_safe(id)}.json"
        with open(file, "r") as f:
            content = Content(**json.load(f))
        return content

    def delete(self, id: str) -> None:
        content = self.get_content(id)
        file = self.home_dir / f"{make_filesystem_safe(id)}.json"
        file.unlink()
        self.segments.delete(
            ids=[get_sha256_hash(f"{id}-{p}") for p in content.passages]
        )
        self.content.delete(ids=[id])

    def retrieve(
        self,
        query: str,
        n_results: int,
        filter_keys: list[str],
    ) -> tuple[list[Content], list[float]]:
        filter_keys = filter_keys or []
        results = self.segments.query(
            query_texts=[query],
            n_results=n_results,
            where={"id": {"$in": filter_keys}} if filter_keys else None,  # type: ignore
        )

        retrieved_content: dict[str, Content] = {}
        if not results or not results["metadatas"] or not results["distances"]:
            return [], []

        for metadata in results["metadatas"][0]:
            id = str(metadata["id"])
            passage = str(metadata["passage"])
            if id not in retrieved_content:
                retrieved_content[id] = self.get_content(id)
                retrieved_content[id].passages = []
            retrieved_content[id].passages.append(passage)

        return list(retrieved_content.values()), results["distances"][0]
