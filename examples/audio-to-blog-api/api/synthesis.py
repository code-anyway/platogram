from hashlib import sha256
from io import TextIOWrapper
import platogram as plato
import os # import specifics
from tempfile import TemporaryDirectory
from typing import Tuple
from urllib import request

CACHE_DIR = Path("./.platogram-cache")

def is_valid_url(url: str) -> bool:
    try:
        res = request.urlopen(url)
        return res.getcode() == 200
    except urllib.request.HTTPError as e:
        raise e


def get_audio_url(src: str | TextIOWrapper) -> str:
    if type(src) == str and is_valid_url(src):
        return src
    else:
        # Change to handle file type
        dest_file =  f"{CACHE_DIR}/{sha256(src.read())}"
        src.save(dest_file)
        return f"file://{os.path.abs(dest_file)}"


def summarize_audio(src: str | TextIOWrapper, anthropic_model: str = "claude-3-5-sonnet", assembly_ai_model: str = "best") -> plato.Content:
    key = os.environ["ANTHROPIC_API_KEY"]
    llm = plato.llm.get_model(anthropic_model, os.environ["ANTHROPIC_API_KEY"])
    asr = plato.asr.get_model(assembly_ai_model,os.environ["ASSEMBLYAI_API_KEY"])

    url = get_audio_url(src)

    transcript = plato.extract_transcript(url, asr)
    content = plato.index(transcript, llm)

    return content
