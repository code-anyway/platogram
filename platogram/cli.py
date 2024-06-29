import argparse
import sys
from urllib.parse import urlparse
from pathlib import Path
import platogram as plato
import re

CACHE_DIR = Path("./.platogram-cache")


def format_time(ms):
    seconds = ms // 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def render_reference(content, i, url):
    link = f" [[{i+1}]]({url}#t={content.transcript[i].time_ms // 1000})"
    return link


def render_transcript(first, last, transcript, url):
    return "\n".join(
        [
            f"{i-first+1}. [{format_time(event.time_ms)}]({url}#t={event.time_ms // 1000}): {event.text}"
            for i, event in enumerate(transcript)
            if first <= i <= last
        ]
    )


def render_paragraph(p: str, content: plato.Content, url: str) -> str:
    references = sorted([int(i) for i in re.findall(r"【(\d+)】", p)])
    if not references:
        return p

    paragraph = re.sub(
        r"【(\d+)】",
        lambda match: render_reference(content, int(match.group(1)), url),
        p,
    )

    return paragraph


def render_content(content: plato.Content, url: str) -> str:
    markdown = "\n\n".join(
        [render_paragraph(p, content, url) for p in content.paragraphs]
    )

    return f"""
# {content.title}
{content.short_summary}
## Summary
{content.summary}
## Content
{markdown}
"""


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
        content = plato.Content.model_validate_json(open(cache_file).read())
    else:
        print(f"Extracting transcript for {url}", file=sys.stderr)
        transcript = plato.extract_transcript(url, asr)
        print("Indexing content", file=sys.stderr)
        content = plato.index(transcript, llm)
        open(cache_file, "w").write(content.model_dump_json(indent=2))

    return content


def prompt_content(content, prompt, context_size, anthropic_api_key):
    llm = plato.llm.get_model("anthropic/claude-3-5-sonnet", anthropic_api_key)
    response = llm.prompt(
        prompt=prompt,
        context=[content],
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
    parser.add_argument("url_or_file", help="URL or file to process")
    parser.add_argument("--anthropic-api-key", required=True, help="Anthropic API key")
    parser.add_argument("--assemblyai-api-key", help="AssemblyAI API key")
    parser.add_argument("--prompt", help="Prompt for content generation")
    parser.add_argument(
        "--context-size",
        choices=["small", "medium", "large"],
        default="small",
        help="Context size for prompting",
    )
    parser.add_argument("--transcript", action="store_true", help="Include transcript")
    args = parser.parse_args()

    if is_uri(args.url_or_file):
        url = args.url_or_file
    else:
        if not Path(args.url_or_file).exists():
            raise FileNotFoundError(args.url_or_file)
        url = f"file://{Path(args.url_or_file)}"

    content = process_url(url, args.anthropic_api_key, args.assemblyai_api_key)

    if args.prompt:
        result = prompt_content(
            content, args.prompt, args.context_size, args.anthropic_api_key
        )
        print(render_paragraph(result, content, url))
    else:
        print(render_content(content, url))

    if args.transcript:
        print("\n## Transcript\n")
        print(render_transcript(0, len(content.transcript), content.transcript, url))


if __name__ == "__main__":
    main()
