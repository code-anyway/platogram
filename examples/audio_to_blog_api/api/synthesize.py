from hashlib import sha256
from io import TextIOWrapper
import platogram as plato
import os
from tempfile import NamedTemporaryFile
from typing import Tuple
from urllib import request


CACHE_DIR = Path("./.platogram-cache")


def is_valid_url(url: str) -> bool:
    try:
        res = request.urlopen(url)
        return res.getcode() == 200
    except urllib.request.HTTPError as e:
        raise e


def get_audio_url(src: str | TextIOWrapper, temp_dir: TemporaryDirectory | None) -> str:
    if type(src) == str and is_valid_url(src):
        return src
    else:
        # Change to handle file type
        dest_file =  f"{temp_dir.name}/{sha256(src.read())}"
        src.save(dest_file)
        return f"file://{os.path.abs(dest_file)}"


def summarize_audio(
        src: str | TextIOWrapper,
        anthropic_model: str = "claude-3-5-sonnet",
        assembly_ai_model: str = "best"
    ) -> Tuple[str, plato.Content]:
    llm = plato.llm.get_model(anthropic_model, os.environ["ANTHROPIC_API_KEY"])
    asr = plato.asr.get_model(assembly_ai_model,os.environ["ASSEMBLYAI_API_KEY"])

    with TemporaryDirectory() as temp_dir:
        url = get_audio_url(src, temp_dir)

        transcript = plato.extract_transcript(url, asr)
    content = plato.index(transcript, llm)

    return content
