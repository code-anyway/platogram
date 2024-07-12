import platogram
from platogram.types import Content, SpeechEvent
import json


def test_get_meta() -> None:
    llm = platogram.llm.get_model("anthropic/claude-3-5-sonnet")
    text = "In this video, we're going to talk about the basics of machine learning.【0】Machine learning is a field of artificial intelligence that focuses on building algorithms that can learn from data and make predictions or decisions without being explicitly programmed.【1】There are three main types of machine learning: supervised learning, unsupervised learning, and reinforcement learning.【2】Supervised learning involves training a model on labeled data, where the correct output is known for each input.【3】The goal is for the model to learn a mapping from inputs to outputs that can be applied to new, unseen data.【4】Unsupervised learning, on the other hand, involves finding patterns or structure in unlabeled data.【5】The model is not given any explicit guidance on what the correct output should be.【6】Reinforcement learning is a type of machine learning where an agent learns to make decisions by interacting with an environment and receiving rewards or punishments based on its actions.【7】The goal is for the agent to learn a policy that maximizes its cumulative reward over time.【8】Machine learning has many practical applications, such as image recognition, natural language processing, and recommendation systems.【9】It's an exciting and rapidly evolving field with the potential to transform many industries and solve complex problems.【10】"
    meta = llm.get_meta([text])
    assert meta


def test_get_chapters() -> None:
    llm = platogram.llm.get_model("anthropic/claude-3-5-sonnet")
    chapters = llm.get_chapters(
        ["First Asset Sentence one and two【0】", "First Asset Sentence three【2】"]
    )
    assert chapters


def test_prompt() -> None:
    llm = platogram.llm.get_model("anthropic/claude-3-5-sonnet")

    context = []

    with open("samples/jfk.json") as f:
        context.append(Content(**json.load(f)))

    with open("samples/obama.json") as f:
        context.append(Content(**json.load(f)))

    text = llm.prompt(
        "Compare the summaries of two inauguration speeches in <context> and write a detailed report.",
        context=context,
        context_size="small",
    )

    assert text


def test_render_context() -> None:
    llm = platogram.llm.get_model("anthropic/claude-3-5-sonnet")
    context = [
        Content(
            title="First Asset",
            summary="First Asset Summary",
            transcript=[
                SpeechEvent(time_ms=0, text="First Asset Sentence one."),
                SpeechEvent(time_ms=1000, text="First Asset Sentence two."),
                SpeechEvent(time_ms=2000, text="First Asset Sentence three."),
            ],
            passages=[
                "First Asset Sentence one and two【0】",
                "First Asset Sentence three【2】",
            ],
            chapters={
                0: "First Asset Sentence one and two",
                2: "First Asset Sentence three",
            },
        ),
        Content(
            title="Second Asset",
            summary="Second Asset Summary",
            transcript=[
                SpeechEvent(time_ms=0, text="Second Asset Sentence one."),
                SpeechEvent(time_ms=1000, text="Second Asset Sentence two."),
                SpeechEvent(time_ms=2000, text="Second Asset Sentence three."),
            ],
            passages=[
                "Second Asset Sentence one and two【0】",
                "Second Asset Sentence three【2】",
            ],
            chapters={
                0: "Second Asset Sentence one and two",
                2: "Second Asset Sentence three",
            },
        ),
    ]

    text = llm.render_context(context, "medium")
    assert (
        text
        == """<content title="First Asset" summary="First Asset Summary">
<text>First Asset Sentence one.【0】First Asset Sentence two.【1】First Asset Sentence three.【2】</text>
</content>
<content title="Second Asset" summary="Second Asset Summary">
<text>Second Asset Sentence one.【3】Second Asset Sentence two.【4】Second Asset Sentence three.【5】</text>
</content>"""
    )

    text = llm.render_context(context, "small")
    assert (
        text
        == """<content title="First Asset" summary="First Asset Summary">
<paragraphs>
<p>First Asset Sentence one and two【0】</p>
<p>First Asset Sentence three【2】</p>
</paragraphs>
</content>
<content title="Second Asset" summary="Second Asset Summary">
<paragraphs>
<p>Second Asset Sentence one and two【3】</p>
<p>Second Asset Sentence three【5】</p>
</paragraphs>
</content>"""
    )

    text = llm.render_context(context, "large")
    assert (
        text
        == """<content title="First Asset" summary="First Asset Summary">
<paragraphs>
<p>First Asset Sentence one and two【0】</p>
<p>First Asset Sentence three【2】</p>
</paragraphs>
<text>First Asset Sentence one.【0】First Asset Sentence two.【1】First Asset Sentence three.【2】</text>
</content>
<content title="Second Asset" summary="Second Asset Summary">
<paragraphs>
<p>Second Asset Sentence one and two【3】</p>
<p>Second Asset Sentence three【5】</p>
</paragraphs>
<text>Second Asset Sentence one.【3】Second Asset Sentence two.【4】Second Asset Sentence three.【5】</text>
</content>"""
    )
