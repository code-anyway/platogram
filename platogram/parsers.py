import json
import re
from pathlib import Path

from platogram.types import SpeechEvent
from platogram.utils import parse_hh_mm_ss


def remove_special_characters(line: str) -> str:
    """Removes special characters from line."""

    return line.replace("&nbsp;", " ").replace("&amp;", "&")


def parse_lrc(text: str) -> list[SpeechEvent]:
    """
    Parses .lrc subtitle format into a list of Events.

    Args:
        text: content of .lrc file.
        str: unused, present to match function signature.

    Returns:
        A list of Events parsed from .lrc.
    """
    events = []
    pattern = re.compile(r"\[(\d+):(\d{2})\.(\d{2})\](.*)")
    for line in text.split("\n"):
        match = pattern.match(line)
        if match:
            minutes, seconds, centiseconds, content = match.groups()
            time_ms = (
                (int(minutes) * 60 * 1000)
                + (int(seconds) * 1000)
                + (int(centiseconds) * 10)
            )
            events.append(SpeechEvent(time_ms=time_ms, text=content))
    return events


def parse_vtt(text: str) -> list[SpeechEvent]:
    """Generates sequence of Events from subtitles stored in .vtt format.

    Args:
        text: content of .vtt file.

    Returns:
        Speech events parsed from .vtt.
    """
    if not text.endswith("\n"):
        text += "\n"
    parser = re.compile(r"([\d\:\.]+)\s*-->\s*([\d\:\.]+)\n((.+\n)+)")
    match = parser.findall(text)
    result = []

    for start, finish, text, _ in match:
        result += [
            SpeechEvent(
                time_ms=parse_hh_mm_ss(start),
                text=" ".join(
                    [remove_special_characters(line) for line in text.split("\n")[:-1]]  # noqa: E501
                ),  # there is an extra newline in .vtt format # noqa: E501
            )
        ]

    return result


def parse_subtitles(file: Path) -> list[SpeechEvent]:
    if file.suffix == ".vtt":
        return parse_vtt(file.read_text())
    elif file.suffix == ".lrc":
        return parse_lrc(file.read_text())
    else:
        raise ValueError(f"Unsupported subtitle file format: {file.suffix}")


def parse_waffly(file: Path) -> list[SpeechEvent]:
    if file.suffix != ".json":
        raise ValueError(
            f"Expected file extension to be '.json', but got {file.suffix}"
        )

    with open(file, "r") as f:
        raw = json.load(f)

    if raw and "sentences" in raw[0]:
        sentences: list[dict] = sum([phrase["sentences"] for phrase in raw], [])
        return [
            SpeechEvent(time_ms=sentence["start"], text=sentence["text"])
            for sentence in sentences
        ]
    else:
        return [
            SpeechEvent(time_ms=start, text=text, speaker=speaker)
            for text, start, speaker in [
                (word["text"], int(word["start"]), word["speaker"]) for word in raw
            ]
        ]
