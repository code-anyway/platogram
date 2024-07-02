import argparse
import sys
from urllib.parse import urlparse
from pathlib import Path
import platogram as plato
from platogram.types import User, Assistant, Content
import re
from typing import Callable, Literal, Sequence


CACHE_DIR = Path("./.platogram-cache")


def format_time(ms):
    seconds = ms // 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def render_reference(url: str, transcript: list[plato.SpeechEvent], i: int) -> str:
    link = f" [[{i+1}]]({url}#t={transcript[i].time_ms // 1000})"
    return link


def render_transcript(first, last, transcript, url):
    return "\n".join(
        [
            f"{i-first+1}. [{format_time(event.time_ms)}]({url}#t={event.time_ms // 1000}): {event.text}"
            for i, event in enumerate(transcript)
            if first <= i <= last
        ]
    )


def render_paragraph(p: str, render_reference_fn: Callable[[int], str]) -> str:
    references = sorted([int(i) for i in re.findall(r"【(\d+)】", p)])
    if not references:
        return p

    paragraph = re.sub(
        r"【(\d+)】",
        lambda match: render_reference_fn(int(match.group(1))),
        p,
    )

    return paragraph


def make_file_name(url: str) -> str:
    # transform url into a file name replacing non-alphanumeric characters with dashes
    return re.sub(r"\W+", "-", url)


def process_url(url, anthropic_api_key, assemblyai_api_key=None):
    llm = plato.llm.get_model("anthropic/claude-3-5-sonnet", anthropic_api_key)
    asr = (
        plato.asr.get_model("assembly-ai/best", assemblyai_api_key)
        if assemblyai_api_key
        else None
    )

    CACHE_DIR.mkdir(exist_ok=True)

    cache_file = CACHE_DIR / f"{make_file_name(url)}.json"
    if cache_file.exists():
        # read from json into pydantic model
        content = Content.model_validate_json(open(cache_file).read())
    else:
        print(f"Extracting transcript for {url}", file=sys.stderr)
        transcript = plato.extract_transcript(url, asr)
        print("Indexing content", file=sys.stderr)
        content = plato.index(transcript, llm)
        open(cache_file, "w").write(content.model_dump_json(indent=2))

    return content


def prompt_content(
    content: list[Content],
    prompt: Sequence[Assistant | User],
    context_size: Literal["small", "medium", "large"],
    anthropic_api_key: str | None,
) -> str:
    llm = plato.llm.get_model("anthropic/claude-3-5-sonnet", anthropic_api_key)
    response = llm.prompt(
        prompt=prompt,
        context=content,
        context_size=context_size,
    )
    return response


def is_uri(s):
    try:
        result = urlparse(s)
        return all([result.scheme, result.netloc, result.path])
    except:
        return False


def main():
    parser = argparse.ArgumentParser(description="Platogram CLI")
    parser.add_argument("url_or_file", nargs="?", help="URL or file to process")
    parser.add_argument("--anthropic-api-key", help="Anthropic API key")
    parser.add_argument("--assemblyai-api-key", help="AssemblyAI API key")
    parser.add_argument("--prompt", help="Prompt for content generation")
    parser.add_argument(
        "--context-size",
        choices=["small", "medium", "large"],
        default="small",
        help="Context size for prompting",
    )
    parser.add_argument("--title", action="store_true", help="Include title")
    parser.add_argument("--abstract", action="store_true", help="Include abstract")
    parser.add_argument("--passages", action="store_true", help="Include passages")
    parser.add_argument("--references", action="store_true", help="Include references")
    parser.add_argument("--origin", action="store_true", help="Include origin URL")
    parser.add_argument(
        "--prefill",
        default="",
        help="Nudge the model to continue the provided sentence",
    )
    parser.add_argument(
        "--inline-references", action="store_true", help="Render references inline"
    )
    args = parser.parse_args()

    if not args.url_or_file:
        if CACHE_DIR.exists():
            files = CACHE_DIR.glob("*.json")
            urls = [f"file://{str(file)}" for file in files]
        else:
            print(
                "No cached content found in .platogram-cache. Please provide a URL or file.",
                file=sys.stderr,
            )
            return
    else:
        urls = [
            url if is_uri(url) else f"file://{Path(url)}" for url in [args.url_or_file]
        ]

    print(f"Processing: {urls}", file=sys.stderr)
    content = [
        process_url(url, args.anthropic_api_key, args.assemblyai_api_key)
        for url in urls
    ]

    result = ""
    if args.prompt:
        if args.prefill:
            prompt = [User(content=args.prompt), Assistant(content=args.prefill)]
        else:
            prompt = [User(content=args.prompt)]

        result += f"""\n\n{
            prompt_content(
                content, prompt, args.context_size, args.anthropic_api_key
            )}\n\n"""

    for c, u in zip(content, urls):
        if args.origin:
            result += f"""\n\n{u}\n\n"""

        if args.title:
            result += f"""\n\n{c.title}\n\n"""

        if args.abstract:
            result += f"""\n\n{c.summary}\n\n"""

        if args.passages:
            passages = "\n\n".join(c.passages)
            result += f"""\n\n{passages}\n\n"""

        if args.references:
            result += f"""\n\n{render_transcript(0, len(c.transcript), c.transcript, u)}\n\n"""

        if args.inline_references:
            render_reference_fn = lambda i: render_reference(u, c.transcript, i)
        else:
            render_reference_fn = lambda _: ""

        result = render_paragraph(result, render_reference_fn)

    print(result)


if __name__ == "__main__":
    main()
