from typing import Protocol, Literal, Generator, Sequence
from platogram.types import Content, User, Assistant


class LanguageModel(Protocol):
    def count_tokens(self, text: str) -> int: ...

    def get_meta(
        self, paragraphs: list[str], max_tokens: int = 4096, temperature: float = 0.5, lang: str | None = None
    ) -> tuple[str, str]: ...

    def get_chapters(
        self, passages: list[str], max_tokens: int = 4096, temperature: float = 0.5, lang: str | None = None
    ) -> dict[int, str]: ...

    def get_paragraphs(
        self,
        text_with_markers: str,
        examples: dict[str, list[str]],
        max_tokens: int = 4096,
        temperature: float = 0.5,
        lang: str | None = None
    ) -> list[str]: ...

    def prompt_model(
        self,
        messages: Sequence[User | Assistant],
        max_tokens: int = 4096,
        temperature=0.1,
        stream=False,
        system: str | None = None,
        tools: list[dict] | None = None,
    ) -> str | dict[str, str] | Generator[str, None, None]: ...

    def prompt(
        self,
        prompt: Sequence[User | Assistant] | str,
        *,
        context: list[Content],
        context_size: Literal["small", "medium", "large"] = "small",
        max_tokens: int = 4096,
        temperature: float = 0.5,
        lang: str | None = None,
    ) -> str: ...

    def render_context(
        self, context: list[Content], context_size: Literal["small", "medium", "large"]
    ) -> str: ...


def get_model(full_model_name: str, key: str | None = None) -> LanguageModel:
    if full_model_name.startswith("anthropic/"):
        from platogram.llm.anthropic import Model

        return Model(full_model_name.split("/")[-1], key)
    else:
        raise ValueError(f"Unsupported language model: {full_model_name}")
