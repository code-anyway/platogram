import platogram

from pathlib import Path
from platogram import ingest


def test_extract_images(tmp_path):
    images = ingest.extract_images(
        "https://www.youtube.com/shorts/XsLK3tPy9SI",
        timestamps_ms=[0],
        output_dir=Path(tmp_path),
    )
    assert images and all(image.exists() for image in images)


def test_slurp_subtitles():
    transcript = ingest.extract_transcript(
        "https://www.youtube.com/watch?v=W3I3kAg2J7w", lang="es"
    )
    assert transcript


def test_slurp_youtube_transcribe():
    asr_model = platogram.asr.get_model("assembly-ai/best")
    transcript = ingest.extract_transcript(
        "https://www.youtube.com/shorts/XsLK3tPy9SI", asr_model
    )
    assert transcript
