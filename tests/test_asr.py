import platogram
from pathlib import Path


def test_transcribe_assemblyai():
    transcript = platogram.asr.get_model("assembly-ai/best").transcribe(
        Path("samples/jfk.ogg")
    )
    assert "work must truly be our own" in transcript[-1].text
