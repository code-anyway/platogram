from hashlib import sha256
from io import TextIOWrapper
from pathlib import Path
import platogram as plato
import os
from tempfile import TemporaryDirectory
from typing import Tuple
from urllib import request


CACHE_DIR = Path("./.platogram-cache")
## Handle cache rotation


def make_file_name(src: str | TextIOWrapper):
    if type(src) == TextIOWrapper:
        src = src.read()
    else:
        src = src.encode()
    hash = sha256(src).hexdigest()
    return hash


def is_valid_url(url: str) -> bool:
    try:
        res = request.urlopen(url)
        return res.getcode() == 200
    except urllib.request.HTTPError as e:
        raise e


async def get_audio_url(src: str | TextIOWrapper, temp_dir: TemporaryDirectory | None) -> str:
    if type(src) == str and is_valid_url(src):
        return src
    else:
        src.seek(0)
        dest_file =  f"{temp_dir.name}/{sha256(src.read()).hexdigest()}"
        await src.save(dest_file)
        return f"file://{os.path.abs(dest_file)}"


async def summarize_audio(
        src: str | TextIOWrapper,
        anthropic_model: str = "claude-3-5-sonnet",
        assembly_ai_model: str = "best"
    ) -> Tuple[str, plato.Content]:
    llm = plato.llm.get_model(f"anthropic/{anthropic_model}", os.environ["ANTHROPIC_API_KEY"])
    asr = plato.asr.get_model(f"assembly-ai/{assembly_ai_model}",os.environ["ASSEMBLYAI_API_KEY"])

    CACHE_DIR.mkdir(exist_ok=True)

    cache_file = CACHE_DIR / f"{make_file_name(src)}.json"

    if cache_file.exists():
        content = plato.Content.model_validate_json(open(cache_file).read())
    else:
        with TemporaryDirectory() as temp_dir:
            url = await get_audio_url(src, temp_dir)
            print(url)

            transcript = plato.extract_transcript(url, asr)
        content = plato.index(transcript, llm)
        open(cache_file, "w").write(content.model_dump_json(indent=2))

    return make_file_name(src), content
