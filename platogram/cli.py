import argparse
import os
import platogram as plato
from IPython.display import display, Markdown
import re

CACHE_DIR = "./.platogram-cache"

def format_time(ms):
    seconds = ms // 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def render_reference(i, first, url):
    link = f" [[{i-first+1}]]({url}#t={i.time_ms // 1000})"
    return link

def render_transcript(first, last, transcript, url):
    return "<br>".join([
        f"{i+1}. <a href='{url}#t={t.time_ms // 1000}'>{format_time(t.time_ms)}</a>: {t.text}"
        for i, t in enumerate(transcript[first:last+1])
    ])

def render_paragraph(p, content):
    references = sorted([int(i) for i in re.findall(r"【(\d+)】", p)])
    if not references:
        return p

    first = references[0]
    last = references[-1]

    paragraph = re.sub(
        r"【(\d+)】",
        lambda match: render_reference(content.transcript[int(match.group(1))], first, content.url),
        p
    )
    transcript = render_transcript(first, last, content.transcript, content.url)
    return f"{paragraph}\n<details><summary>Transcript</summary>{transcript}</details>"

def render_content(content):
    markdown = "\n\n".join([
        render_paragraph(p, content)
        for p in content.paragraphs
    ])

    return f"""
# {content.title}
{content.short_summary}
## Summary
{content.summary}
## Content
{markdown}
"""

def process_url(url, anthropic_api_key, assemblyai_api_key=None):
    llm = plato.llm.get_model("anthropic/claude-3-5-sonnet", anthropic_api_key)
    asr = plato.asr.get_model("assembly-ai/best", assemblyai_api_key) if assemblyai_api_key else None

    cache_file = os.path.join(CACHE_DIR, f"{hash(url)}.json")
    if os.path.exists(cache_file):
        content = plato.Content.load(cache_file)
    else:
        transcript = plato.extract_transcript(url, asr)
        content = plato.index(transcript, llm)
        os.makedirs(CACHE_DIR, exist_ok=True)
        content.save(cache_file)

    return content

def prompt_content(content, prompt, context_size, anthropic_api_key):
    llm = plato.llm.get_model("anthropic/claude-3-5-sonnet", anthropic_api_key)
    response = llm.prompt(
        prompt=prompt,
        context=[content],
        context_size=context_size,
    )
    return render_paragraph(response, content)

def main():
    parser = argparse.ArgumentParser(description="Platogram CLI")
    parser.add_argument("url", help="URL to process")
    parser.add_argument("--anthropic-api-key", required=True, help="Anthropic API key")
    parser.add_argument("--assemblyai-api-key", help="AssemblyAI API key")
    parser.add_argument("--prompt", help="Prompt for content generation")
    parser.add_argument("--context-size", choices=["small", "medium", "large"], default="small", help="Context size for prompting")
    args = parser.parse_args()

    content = process_url(args.url, args.anthropic_api_key, args.assemblyai_api_key)
    
    if args.prompt:
        result = prompt_content(content, args.prompt, args.context_size, args.anthropic_api_key)
        print(result)
    else:
        print(render_content(content))

if __name__ == "__main__":
    main()