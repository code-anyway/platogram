import os
import re
import json
from pathlib import Path

import chromadb

from platogram.types import Content
from platogram.utils import get_sha256_hash
from platogram.ops import remove_markers


from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction


EMBEDDING_MODEL = "text-embedding-3-large"


def make_filesystem_safe(s):
    # Remove leading and trailing whitespace
    s = s.strip()
    # Replace spaces with underscores
    s = s.replace(" ", "_")
    # Remove or replace invalid characters
    s = re.sub(r"[^\w\-\.]", "", s)
    # Optional: truncate the string to a max length, e.g., 255 characters
    return s[:255]


class LocalLibrary:
    def __init__(self, home_dir: Path):
        if not home_dir.exists():
            home_dir.mkdir(parents=True)
        self.home_dir = home_dir

        self.client = chromadb.PersistentClient(path=str(home_dir / "chroma.index"))

        embedding_function = OpenAIEmbeddingFunction(
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

    def exists(self, id: str) -> bool:
        return bool(self.content.get(ids=[id])["ids"])

    def put(self, id: str, content: Content) -> None:
        file = self.home_dir / f"{make_filesystem_safe(id)}.json"
        with open(file, "w") as f:
            json.dump(content.dict(), f)

        self.content.add(
            documents=[f"{content.title} {content.summary}"],
            ids=[id],
        )

        self.segments.add(
            documents=[remove_markers(p) for p in content.paragraphs],
            metadatas=[{"id": id} for _ in content.paragraphs],
            ids=[get_sha256_hash(f"{id}-{p}") for p in content.paragraphs],
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
            ids=[get_sha256_hash(f"{id}-{p}") for p in content.paragraphs]
        )
        self.content.delete(ids=[id])

    def retrieve(
        self,
        query: str,
        n_results: int,
        filter_keys: list[str] = [],
    ) -> list[Content]:
        results = self.segments.query(
            query_texts=[query],
            n_results=n_results,
            where={"id": {"$in": filter_keys}} if filter_keys else None,  # type: ignore
        )
        return [
            self.get_content(str(metadata["id"]))
            for metadata in results["metadatas"][0]  # type: ignore
        ]
