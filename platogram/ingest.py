import logging
import mimetypes
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory

import requests  # type: ignore
from yt_dlp import YoutubeDL  # type: ignore
import subprocess

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


def get_subtitle_languages(url: str) -> list[str]:
    if not has_subtitles(url):
        raise ValueError(f"No subtitles found for {url}")

    all_languages = list(get_metadata(url).get("subtitles", {}).keys())
    if not all_languages:
        raise ValueError(f"No subtitles found for {url}")

    return all_languages


def download_subtitles(url: str, output_dir: Path, lang: str | None = None) -> Path:
    if not lang:
        lang = "en"

    for subtitle_lang in get_subtitle_languages(url):
        if subtitle_lang.lower().startswith(lang.lower()[:2]):
            lang = subtitle_lang
            break

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


def download_video(url: str, output_dir: Path) -> Path | None:
    filename = get_id(url)
    file_path = output_dir / filename

    if url.lower().startswith("file://"):
        return Path(url.replace("file://", ""))

    try:
        with YoutubeDL(
            {
                "format": "bestvideo/best",
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
    except Exception as e:
        logger.warning(f"Failed to download video: {e}")
        return None


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


def extract_images(
    url: str, output_dir: Path, timestamps_ms: list[int] | None = None
) -> list[Path]:
    """
    Extracts images from a video at the specified timestamps.

    Args:
        url (str): The URL of the video.
        timestamps_ms (list[int], optional): A list of timestamps in milliseconds at which to extract images.
            If not provided, a single image will be extracted at the start of the video.

    Returns:
        list[Path]: A list of file paths to the extracted images.
    """
    video_path = download_video(url, output_dir)

    if timestamps_ms is None:
        timestamps_ms = [0]

    image_paths = []
    try:
        for timestamp_ms in timestamps_ms:
            timestamp_s = timestamp_ms / 1000
            image_path = Path(output_dir) / f"image_{timestamp_ms:09d}.png"

            subprocess.run(
                [
                    "ffmpeg",
                    "-ss",
                    f"{timestamp_s:.3f}",
                    "-i",
                    str(video_path),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    "-f",
                    "image2",
                    str(image_path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            image_paths.append(image_path)
    finally:
        # Delete the downloaded video file
        if video_path:
            video_path.unlink()

    return image_paths


def extract_transcript(
    url: str, asr_model: ASRModel | None = None, lang: str | None = None
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
            speech_events = asr_model.transcribe(file, lang=lang)
        elif has_subtitles(url):
            speech_events = parse_subtitles(
                download_subtitles(url, Path(temp_dir), lang=lang)
            )
        else:
            raise ValueError("No subtitles found and no ASR model provided.")

        return speech_events
