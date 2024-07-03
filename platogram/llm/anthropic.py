import re
from typing import Generator, Any
import os

import anthropic
from anthropic import AnthropicError
from tenacity import (
    retry,
    stop_after_attempt,
    stop_after_delay,
    retry_if_exception_type,
)
from platogram.types import Content
from platogram.ops import render
from typing import Literal
from platogram.types import User, Assistant
from typing import Sequence


RETRY = retry(
    stop=(stop_after_delay(300) | stop_after_attempt(5)),
    retry=retry_if_exception_type(AnthropicError),
)


class Model:
    def __init__(self, model: str, key: str | None = None) -> None:
        if key is None:
            key = os.environ["ANTHROPIC_API_KEY"]

        if model == "claude-3-haiku":
            self.model = "claude-3-haiku-20240307"
        elif model == "claude-3-opus":
            self.model = "claude-3-opus-20240229"
        elif model == "claude-3-sonnet":
            self.model = "claude-3-sonnet-20240229"
        elif model == "claude-3-5-sonnet":
            self.model = "claude-3-5-sonnet-20240620"
        else:
            raise ValueError(f"Unknown model: {model}")

        self.client = anthropic.Client(api_key=key)

    def count_tokens(self, text: str) -> int:
        return self.client.count_tokens(text)

    def prompt_model(
        self,
        messages: Sequence[User | Assistant],
        max_tokens: int = 4096,
        temperature=0.1,
        stream=False,
        system: str | None = None,
        tools: list[dict] | None = None,
    ) -> str | dict[str, str] | Generator[str, None, None]:
        kwargs: dict[str, Any] = {}

        if tools:
            kwargs["tools"] = tools

        if system:
            kwargs["system"] = system

        if not stream:

            @RETRY
            def get_response(messages):
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": m.role, "content": m.content} for m in messages],
                    **kwargs,
                )

                if response.stop_reason == "tool_use":
                    return response.content[-1].input

                return response.content[0].text

            return get_response(messages)

        def stream_text():
            with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                **kwargs,
            ) as stream:

                @RETRY
                def get_response():
                    while True:
                        for text in stream.text_stream:
                            yield text
                        break

                return get_response()

        return stream_text()

    def get_meta(
        self, paragraphs: list[str], max_tokens: int = 4096, temperature: float = 0.5
    ) -> tuple[str, str]:
        system_prompt = """<role>
You are a very capable editor, speaker, educator, and author with a knack for coming up with meta information about the content.
</role>
<task>
You will be given a <text> that contains paragraphs enclosed in <p></p> tags and you will need to come up with meta information about the content.
</task>
""".strip()
        properties = {
            "title": "Come up with the title which speaks to the essence of the content. Use simple language.",
            "summary": "Distill the key insights and express them as a short story using simple language. Make sure to cover all parts of the summary.",
        }

        tool_definition = {
            "name": "render_meta",
            "description": "Renders meta information about the content.",
            "input_schema": {
                "type": "object",
                "properties": {
                    name: {"type": "string", "description": description}
                    for name, description in properties.items()
                },
                "required": list(properties.keys()),
            },
        }

        text = "\n".join([f"<p>{paragraph}</p>" for paragraph in paragraphs])

        meta = self.prompt_model(
            system=system_prompt,
            messages=[User(content=f"<text>{text}</text>")],
            tools=[tool_definition],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        assert isinstance(
            meta, dict
        ), f"Expected LLM to return dict with meta information, got {meta}"
        return meta["title"], meta["summary"]

    def get_paragraphs(
        self,
        text_with_markers: str,
        examples: dict[str, list[str]],
        max_tokens: int = 4096,
        temperature: float = 0.5,
    ) -> list[str]:
        system_prompt = """<role>
You are a very capable editor, speaker, educator, and author who is really good at reading text that represents transcript of human speech and rewriting it into well-structured, information-dense written text.
</role>
<task>
You will be given speech <transcript> in a format "text【0】text【1】... text 【2】". Where each【number】is a <marker> and goes AFTER the text it references. Markers are zero-based and are in sequential order.

Follow these steps to rewrite the <transcript> and keep every <marker>:
1. Study the message history carefully and understand how <transcript> is rewritten into series well-structured <paragraphs>.
2. Return a series well-structured <paragraphs>, enclose each paragraph into <p></p> as shown in message history.
3. Make sure to keep every <marker> in the <transcript> in the same order as it appears in the <transcript>.
</task>""".strip()

        def format_examples() -> Generator[tuple[str, str], None, None]:
            for prompt, paragraphs in examples.items():
                yield (
                    prompt,
                    "\n".join([f"<p>{paragraph}</p>" for paragraph in paragraphs]),
                )

        example_messages: list[User | Assistant] = []
        for prompt, response in format_examples():
            example_messages.append(User(content=f"<transcript>{prompt}</transcript>"))
            example_messages.append(
                Assistant(content=f"<paragraphs>{response}</paragraphs>")
            )

        paragraphs = self.prompt_model(
            max_tokens=max_tokens,
            messages=[
                *example_messages,
                User(content=f"<transcript>{text_with_markers}</transcript>"),
                Assistant(content="<paragraphs><p>"),
            ],
            system=system_prompt,
            temperature=temperature,
        )
        assert isinstance(
            paragraphs, str
        ), f"Expected LLM to return str, got {paragraphs}"
        return re.findall(r"<p>(.*?)</p>", paragraphs, re.DOTALL)

    def render_context(
        self, context: list[Content], context_size: Literal["small", "medium", "large"]
    ) -> str:
        base = 0
        output = ""

        for content in context:
            text = render(
                {i + base: event.text for i, event in enumerate(content.transcript)}
            )
            paragraphs = [
                re.sub(r"【(\d+)】", lambda m: f"【{int(m.group(1))+base}】", paragraph)
                for paragraph in content.passages
            ]
            paragraphs = [
                re.sub(
                    r"【(\d+)】(\w*【\d+】\w*)+",
                    lambda m: f"【{int(m.group(1))}】",
                    paragraph,
                )
                for paragraph in paragraphs
            ]
            output += f'<content title="{content.title}" summary="{content.summary}">\n'
            if context_size == "small" or context_size == "large":
                output += "<paragraphs>\n"
                output += "\n".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)
                output += "\n</paragraphs>\n"

            if context_size == "medium" or context_size == "large":
                output += f"<text>{text}</text>\n"

            output += "</content>\n"
            base += len(content.transcript)

        return output.strip()

    def prompt(
        self,
        prompt: Sequence[User | Assistant] | str,
        *,
        context: list[Content],
        context_size: Literal["small", "medium", "large"] = "small",
        max_tokens: int = 4096,
        temperature: float = 0.5,
    ) -> str:
        system_prompt = """<role>
You are a very capable editor, speaker, educator, and author who is really good at researching sources and coming up with information dense responses to prompts backed by references from the context.
</role>
<task>
You will be given a <context> and a <prompt>. Each <content> in <context> is a source of information that you can use to construct <response>.
Each <content> has title and summary attributes that describe the content of the <content>.
Each <content> has either <text>, or <paragraphs>, or both.
<text> is a transcript of human speech and <paragraphs> is a list of well-structured paragraphs enclosed in <p></p>.
<text> and <paragraphs> contain special markers in the format of "text【number】text【number】... text 【number】". All numbers are unique. If more than one <marker> follows text, they both are considered as one marker.
When constructing response, make sure to transfer the ALL original markers from <context> to <response> that support your response.

Follow the steps in <scratchpad> to construct <response> that is well-structured, information-dense, covers all parts of the <prompt> and <context>, and is grounded in the <context>.
</task>
<scratchpad>
1. Study the <context> carefully.
2. Generate <response> based on the <prompt> and <context>.
3. Review the response and make sure it is factually correct based on the <context>.
4. Transfer all the relevant markers from <context> to <response> to support your response.
</scratchpad>
""".strip()

        if isinstance(prompt, str):
            prompt = [User(content=prompt)]

        response = self.prompt_model(
            max_tokens=max_tokens,
            messages=[
                User(
                    content=f"""<context>
{self.render_context(context, context_size)}
</context>
<prompt>
{prompt}
</prompt>"""
                )
            ],
            system=system_prompt,
            temperature=temperature,
        )
        assert isinstance(response, str), f"Expected LLM to return str, got {response}"
        return response
