import os
from pathlib import Path
import assemblyai as aai  # type: ignore
import subprocess
from tempfile import TemporaryDirectory
from platogram.types import SpeechEvent


def convert_to_mp3(file: Path, output_dir: Path) -> Path:
    """
    Converts an audio or video file to MP3 format using ffmpeg.

    Args:
    file: Path to the input file.

    Returns:
    Path to the converted MP3 file.
    """
    if not file.exists():
        raise FileNotFoundError(f"The file {file} does not exist.")

    output_file = output_dir / f"{file.stem}.mp3"

    command = [
        "ffmpeg",
        "-i",
        f'"{str(file)}"',
        "-vn",
        "-ar",
        "44100",
        "-ac",
        "1",
        "-b:a",
        "192k",
        f'"{str(output_file)}"',
    ]
    try:
        command_str = " ".join(command)
        _ = (
            subprocess.check_output(command_str, shell=True, stderr=subprocess.STDOUT)
            .decode("utf-8")
            .strip()
            .replace('"', "")
            .split(",")
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"An error occurred while converting {file} to MP3: {e}. stderr: {e.stderr}"
        )

    return output_file


class Model:
    def __init__(self, model: str = "best", key: str | None = None):
        if model.lower() == "nano":
            self.speech_model = aai.SpeechModel.nano
        elif model.lower() == "best":
            self.speech_model = aai.SpeechModel.best
        else:
            raise ValueError(f"Unknown model: {model}")

        if key is None:
            key = os.getenv("ASSEMBLYAI_API_KEY")
        aai.settings.api_key = key

    def transcribe(self, file: Path, lang: str | None = None) -> list[SpeechEvent]:
        with TemporaryDirectory() as temp_dir:
            if not str(file).endswith(".mp3"):
                file = convert_to_mp3(file, Path(temp_dir))

            if lang is None:
                config = aai.TranscriptionConfig(
                    language_detection=True, speech_model=self.speech_model
                )
            else:
                config = aai.TranscriptionConfig(
                    language_detection=False,
                    language_code=lang,
                    speech_model=self.speech_model,
                )
            transcriber = aai.Transcriber(config=config)
            transcript = transcriber.transcribe(str(file))
            sentences = transcript.get_sentences()
            return [
                SpeechEvent(time_ms=sentence.start, text=sentence.text)
                for sentence in sentences
            ]
