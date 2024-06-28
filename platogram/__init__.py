# import logfire


# logfire.configure()
# logfire.install_auto_tracing(
#    modules=[
#        "platogram.ops",
#        "platogram.asr",
#        "platogram.llm",
#        "platogram.library",
#        "platogram.ingest",
#        "platogram.llm.anthropic",
#        "platogram.asr.assemblyai",
#    ],
#    min_duration=1.0,
# )

from platogram.ops import index, get_paragraphs  # noqa: E402
from platogram.ingest import extract_transcript  # noqa: E402
from platogram import llm, asr, library, ops  # noqa: E402
from platogram.types import Content, SpeechEvent  # noqa: E402


__all__ = [
    "index",
    "extract_transcript",
    "get_paragraphs",
    "llm",
    "asr",
    "library",
    "ops",
    "Content",
    "SpeechEvent",
]
