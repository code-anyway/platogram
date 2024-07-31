import argparse
import re
import sys
from pathlib import Path
from typing import Callable, Literal, Sequence
from urllib.parse import urlparse

from tqdm import tqdm

import platogram as plato
import platogram.ingest as ingest
from platogram.library import Library
from platogram.types import Assistant, Content, User
from platogram.utils import make_filesystem_safe

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


def process_url(
    url: str,
    library: Library,
    anthropic_api_key: str,
    assemblyai_api_key: str | None = None,
    extract_images: bool = False,
    lang: str | None = None,
) -> Content:
    if not lang:
        lang = "en"

    llm = plato.llm.get_model("anthropic/claude-3-5-sonnet", anthropic_api_key)
    asr = (
        plato.asr.get_model("assembly-ai/best", assemblyai_api_key)
        if assemblyai_api_key
        else None
    )
    id = make_filesystem_safe(url)

    if library.exists(id):
        return library.get_content(id)

    with tqdm(total=4, desc=f"Processing {url}", file=sys.stderr) as pbar:
        transcript = plato.extract_transcript(url, asr, lang=lang)
        pbar.update(1)
        pbar.set_description("Indexing content")
        content = plato.index(transcript, llm, lang=lang)
        pbar.update(1)
        if extract_images:
            pbar.set_description("Extracting images")
            images_dir = library.home / id
            images_dir.mkdir(exist_ok=True)
            timestamps_ms = [event.time_ms for event in content.transcript]
            images = ingest.extract_images(url, images_dir, timestamps_ms)
            content.images = [str(image.relative_to(library.home)) for image in images]
            pbar.update(1)
        pbar.set_description("Saving content")
        library.put(id, content)
        pbar.update(1)

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
    parser.add_argument(
        "inputs",
        nargs="*",
        help="URLs and files to query, if none provided, will use all content",
    )
    parser.add_argument("--lang", help="Content language: en, es")
    parser.add_argument("--anthropic-api-key", help="Anthropic API key")
    parser.add_argument("--assemblyai-api-key", help="AssemblyAI API key (optional)")
    parser.add_argument(
        "--retrieve", default=None, help="Number of results to retrieve"
    )
    parser.add_argument("--generate", action="store_true", help="Generate content")
    parser.add_argument("--query", help="Query for retrieval and generation")
    parser.add_argument(
        "--context-size",
        choices=["small", "medium", "large"],
        default="small",
        help="Context size for prompting",
    )
    parser.add_argument("--title", action="store_true", help="Include title")
    parser.add_argument("--abstract", action="store_true", help="Include abstract")
    parser.add_argument("--passages", action="store_true", help="Include passages")
    parser.add_argument("--chapters", action="store_true", help="Include chapters")
    parser.add_argument("--references", action="store_true", help="Include references")
    parser.add_argument("--images", action="store_true", help="Include images")
    parser.add_argument("--origin", action="store_true", help="Include origin URL")
    parser.add_argument(
        "--retrieval-method",
        choices=["keyword", "semantic", "dumb"],
        default="dumb",
        help="Retrieval method",
    )
    parser.add_argument(
        "--prefill",
        default="",
        help="Nudge the model to continue the provided sentence",
    )
    parser.add_argument(
        "--inline-references", action="store_true", help="Render references inline"
    )
    args = parser.parse_args()

    if args.lang:
        lang = args.lang
    else:
        lang = "en"

    if args.retrieval_method == "semantic":
        library = plato.library.get_semantic_local_chroma(CACHE_DIR)
    elif args.retrieval_method == "keyword":
        library = plato.library.get_keyword_local_bm25(CACHE_DIR)
    elif args.retrieval_method == "dumb":
        library = plato.library.get_local_dumb(CACHE_DIR)
    else:
        raise ValueError(f"Invalid retrieval method: {args.retrieval_method}")

    if not args.inputs:
        ids = library.ls()
        context = [library.get_content(id) for id in ids]
    else:
        ids = [make_filesystem_safe(url_or_file) for url_or_file in args.inputs]
        context = [
            process_url(
                url_or_file,
                library,
                args.anthropic_api_key,
                args.assemblyai_api_key,
                extract_images=args.images,
                lang=lang,
            )
            for url_or_file in args.inputs
        ]

    if args.retrieval_method == "keyword":
        library.put(ids[0], context[0])

    if args.retrieve:
        n_results = int(args.retrieve)
        context, scores = library.retrieve(args.query, n_results, ids)

    result = ""
    if args.generate:
        if not args.query:
            raise ValueError("Query is required for generation")

        if args.prefill:
            prompt = [User(content=args.query), Assistant(content=args.prefill)]
        else:
            prompt = [User(content=args.query)]

        result += f"""\n\n{
            prompt_context(
                context, prompt, args.context_size, args.anthropic_api_key,
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

        def get_chapter(passage_marker: int) -> int | None:
            chapter_markers = list(content.chapters.keys())
            for start, end in zip(chapter_markers[:-1], chapter_markers[1:]):
                if start <= passage_marker < end:
                    return start
            if passage_marker >= chapter_markers[-1]:
                return chapter_markers[-1]
            return None

        if args.passages:
            passages = ""
            if args.chapters:
                current_chapter = None
                for passage in content.passages:
                    passage_markers = [int(m) for m in re.findall(r"【(\d+)】", passage)]
                    chapter_marker = get_chapter(passage_markers[0]) if passage_markers else None
                    if chapter_marker is not None and chapter_marker != current_chapter:
                        passages += f"### {content.chapters[chapter_marker]}\n\n"
                        current_chapter = chapter_marker
                    passages += f"{passage.strip()}\n\n"
            else:
                passages = "\n\n".join(
                    passage.strip() for passage in content.passages
                )

            result += f"""{passages}\n\n\n\n"""

        if args.chapters and not args.passages:
            chapters = "\n".join(
                f"- {chapter} [{i}]" for i, chapter in content.chapters.items()
            )
            result += f"""{chapters}\n\n\n\n"""

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
