from typing import Literal

from pydantic import BaseModel


class User(BaseModel):
    role: Literal["user"] = "user"
    content: str


class Assistant(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class SpeechEvent(BaseModel):
    time_ms: int
    text: str
    speaker: str | None = None


class Content(BaseModel):
    title: str
    summary: str
    short_summary: str
    passages: list[str]
    transcript: list[SpeechEvent]
