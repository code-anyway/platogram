from typing import Literal

from pydantic import BaseModel


class User(BaseModel):
    role: Literal["user"] = "user"
    content: str
    cache: bool = False

class Assistant(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str
    cache: bool = False

class SpeechEvent(BaseModel):
    time_ms: int
    text: str
    speaker: str | None = None


class Content(BaseModel):
    title: str
    summary: str
    chapters: dict[int, str]
    passages: list[str]
    transcript: list[SpeechEvent]
    images: list[str] | None = None
    origin: str | None = None
