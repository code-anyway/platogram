import platogram

from platogram import ingest


def test_slurp_subtitles():
    transcript = ingest.extract_transcript(
        "https://www.youtube.com/watch?v=W3I3kAg2J7w"
    )
    assert transcript


def test_slurp_youtube_transcribe():
    asr_model = platogram.asr.get_model("assembly-ai/best")
    transcript = ingest.extract_transcript(
        "https://www.youtube.com/shorts/XsLK3tPy9SI", asr_model
    )
    assert transcript
