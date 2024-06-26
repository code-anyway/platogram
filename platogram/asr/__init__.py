from typing import Protocol
from pathlib import Path
from platogram.types import SpeechEvent


class ASRModel(Protocol):
    def transcribe(self, file: Path, lang: str | None = None) -> list[SpeechEvent]: ...


def get_model(full_model_name: str, key: str | None = None) -> ASRModel:
    if full_model_name.startswith("assembly-ai/"):
        from .assembly import Model

        return Model(full_model_name.split("/")[-1], key)
    else:
        raise ValueError(f"Unsupported ASR model: {full_model_name}")
