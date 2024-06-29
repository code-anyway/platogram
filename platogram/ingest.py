import logging
import mimetypes
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory

import requests  # type: ignore
from yt_dlp import YoutubeDL  # type: ignore

from platogram.parsers import parse_subtitles, parse_waffly
from platogram.asr import ASRModel
from platogram.types import SpeechEvent
from platogram.utils import get_sha256_hash


logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def get_metadata(url: str) -> dict:
    ydl_opts = {"skip_download": True, "quiet": True}
    with YoutubeDL(ydl_opts) as ydl:
        try:
            meta = ydl.extract_info(url, download=False)
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")
            return {}

    return meta  # type: ignore


def has_subtitles(url: str) -> bool:
    return bool(get_metadata(url).get("subtitles", {}))


def subtitle_language(url: str) -> str:
    if not has_subtitles(url):
        raise ValueError(f"No subtitles found for {url}")

    all_languages = list(get_metadata(url).get("subtitles", {}).keys())
    if not all_languages:
        raise ValueError(f"No subtitles found for {url}")

    for lang in all_languages:
        if lang.lower().startswith("en"):
            return lang
    return all_languages[0]


def download_subtitles(url: str, output_dir: Path) -> Path:
    lang = subtitle_language(url)
    with YoutubeDL(
        {
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [lang],
            "subtitlesformat": "vtt",
            "outtmpl": str(output_dir / "subtitles"),
            "skip_download": True,
            "quiet": True,
        }
    ) as ydl:
        ydl.download([url])
        return output_dir / f"subtitles.{lang}.vtt"


def get_id(url: str) -> str:
    if url.lower().startswith("https://drive.google.com"):
        return get_sha256_hash(url)[-8:]

    id = get_metadata(url).get("id", None)
    if not id:
        return get_sha256_hash(url)[-8:]
    return id


def download_audio(url: str, output_dir: Path) -> Path:
    filename = get_id(url)
    file_path = output_dir / filename

    if url.lower().startswith("file://"):
        return Path(url.replace("file://", ""))

    with YoutubeDL(
        {
            "format": "bestaudio/best",
            "outtmpl": f"{file_path}.%(ext)s",
            "external-downloader": "aria2c",
            "external-downloader-args": "-c -j 3 -x 3 -s 3 -k 1M",
            "quiet": True,
        }
    ) as ydl:
        ydl.download([url])

        for file in output_dir.glob(f"{filename}.*"):
            file_path = file
        return file_path


def download_file(url: str, output_dir: Path) -> Path:
    if url.lower().startswith("file://"):
        return Path(url.replace("file://", ""))

    with requests.get(url) as response:
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", None)
        assert content_type is not None, "Content-Type header not found"
        extension = mimetypes.guess_extension(content_type)
        file = output_dir / f"asset{extension}"
        file.write_bytes(response.content)
        return file


def extract_transcript(
    url: str, asr_model: ASRModel | None = None
) -> list[SpeechEvent]:
    """
    Slurps content from a given URL and returns a list of SpeechEvent objects.

    This function can handle various types of content, including:
    - Audio/video content
    - YouTube videos
    - Instagram posts
    - Google Drive files

    If the content has subtitles or requires transcription, it will be processed accordingly.

    The returned SpeechEvent objects contain the following information:
    - text: The transcribed or extracted text content
    - start: The start time of the text segment in seconds
    - end: The end time of the text segment in seconds

    Args:
        url (str): The URL of the content to slurp.

    Returns:
        list[SpeechEvent]: A list of SpeechEvent objects representing the slurped content.
    """
    with TemporaryDirectory() as temp_dir:
        if url.lower().startswith("https://api.waffly"):
            speech_events = parse_waffly(download_file(url, Path(temp_dir)))
        elif asr_model is not None:
            file = download_audio(url, Path(temp_dir))
            speech_events = asr_model.transcribe(file)
        elif has_subtitles(url):
            speech_events = parse_subtitles(download_subtitles(url, Path(temp_dir)))
        else:
            raise ValueError("No subtitles found and no ASR model provided.")

        return speech_events
