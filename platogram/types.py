from pydantic import BaseModel


class SpeechEvent(BaseModel):
    time_ms: int
    text: str
    speaker: str | None = None


class Content(BaseModel):
    title: str
    summary: str
    short_summary: str
    paragraphs: list[str]
    transcript: list[SpeechEvent]
