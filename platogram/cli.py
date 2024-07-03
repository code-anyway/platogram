import argparse
import sys
from urllib.parse import urlparse
from pathlib import Path
import platogram as plato
from platogram.types import User, Assistant, Content
import platogram.ingest as ingest
import re
from typing import Callable, Literal, Sequence
from platogram.library import Library


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


def process_url(
    url: str,
    library: Library,
    anthropic_api_key: str,
    assemblyai_api_key: str | None = None,
    extract_images: bool = False,
) -> Content:
    llm = plato.llm.get_model("anthropic/claude-3-5-sonnet", anthropic_api_key)
    asr = (
        plato.asr.get_model("assembly-ai/best", assemblyai_api_key)
        if assemblyai_api_key
        else None
    )
    id = make_file_name(url)

    if library.exists(id):
        return library.get_content(id)

    print(f"Extracting transcript for {url}", file=sys.stderr)
    transcript = plato.extract_transcript(url, asr)
    print("Indexing content", file=sys.stderr)
    content = plato.index(transcript, llm)
    if extract_images:
        print("Extracting images", file=sys.stderr)
        images_dir = library.home / make_file_name(url)
        images_dir.mkdir(exist_ok=True)
        timestamps_ms = [event.time_ms for event in content.transcript]
        images = ingest.extract_images(url, images_dir, timestamps_ms)
        content.images = [str(image.relative_to(library.home)) for image in images]

    library.put(id, content)

    return content


def prompt_context(
    context: list[Content],
    prompt: Sequence[Assistant | User],
    context_size: Literal["small", "medium", "large"],
    anthropic_api_key: str | None,
) -> str:
    llm = plato.llm.get_model("anthropic/claude-3-5-sonnet", anthropic_api_key)
    response = llm.prompt(
        prompt=prompt,
        context=context,
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
    parser.add_argument("url_or_file", nargs="?", help="URL or file to query")
    parser.add_argument("--anthropic-api-key", help="Anthropic API key")
    parser.add_argument("--assemblyai-api-key", help="AssemblyAI API key (optional)")
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
    parser.add_argument("--images", action="store_true", help="Include images")
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

    library = plato.library.get_local(CACHE_DIR)

    if not args.url_or_file:
        context = [library.get_content(id) for id in library.ls()]
    else:
        context = [
            process_url(
                args.url_or_file,
                library,
                args.anthropic_api_key,
                args.assemblyai_api_key,
                extract_images=args.images,
            )
        ]

    result = ""
    if args.prompt:
        if args.prefill:
            prompt = [User(content=args.prompt), Assistant(content=args.prefill)]
        else:
            prompt = [User(content=args.prompt)]

        result += f"""\n\n{
            prompt_context(
                context, prompt, args.context_size, args.anthropic_api_key
            )}\n\n"""

    for content in context:
        if args.images and content.images:
            images = "\n".join([str(image) for image in content.images])
            result += f"""{images}\n\n\n\n"""

        if args.origin:
            result += f"""{content.origin}\n\n\n\n"""

        if args.title:
            result += f"""{content.title}\n\n\n\n"""

        if args.abstract:
            result += f"""{content.summary}\n\n\n\n"""

        if args.passages:
            passages = "\n\n".join(content.passages)
            result += f"""{passages}\n\n\n\n"""

        if args.references:
            result += f"""{render_transcript(0, len(content.transcript), content.transcript, content.origin)}\n\n\n\n"""

        if args.inline_references:
            render_reference_fn = lambda i: render_reference(
                content.origin or "", content.transcript, i
            )
        else:
            render_reference_fn = lambda _: ""

        result = render_paragraph(result, render_reference_fn)

    print(result)


if __name__ == "__main__":
    main()
