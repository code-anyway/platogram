import json
import re

import platogram as plato
from platogram.ops import render
from platogram.types import Assistant, Content, User

CONTENT: list[str] = [
    # "https://www.youtube.com/watch?v=l8pRSuU81PU",  # Let's reproduce GPT-2
    # "https://www.youtube.com/watch?v=zduSFxRajkE",  # Let's build the GPT Tokenizer
    # "https://www.youtube.com/watch?v=zjkBMFhNj_g",  # [1hr Talk] Intro to Large Language Models
    # "https://www.youtube.com/watch?v=nDLb8_wgX50",  # David Goggins: How to Build Immense Inner Strength
    # "https://www.youtube.com/watch?v=Xu1FMCxoEFc",  # Understanding & Conquering Depression
    # "https://www.youtube.com/watch?v=m_OazsImOiI",  # The Science & Treatment of Bipolar Disorder | Huberman Lab Podcast #82
    # "https://www.youtube.com/watch?v=XJTMQtE-MIo",  # Kevin Spacey: Power, Controversy, Betrayal, Truth & Love in Film and Life | Lex Fridman Podcast #432
    # "https://www.youtube.com/watch?v=NNr6gPelJ3E",  # Roman Yampolskiy: Dangers of Superintelligent AI | Lex Fridman Podcast #431
    # "https://www.youtube.com/watch?v=-DVyjdw4t9I",  # Guido van Rossum: Python and the Future of Programming | Lex Fridman Podcast #341
    # "https://www.youtube.com/watch?v=cdiD-9MMpb0",  # Andrej Karpathy: Tesla AI, Self-Driving, Optimus, Aliens, and AGI | Lex Fridman Podcast #34
    # "https://www.youtube.com/watch?v=_rBPwu2uS-w",  # Smoking is Awesome
]


def evaluate(transcript: str, baseline: str, target: str) -> str:
    model = plato.llm.get_model("anthropic/claude-3-opus")
    system_prompt = """<role>
As a thorough and detail-oriented evaluator, your role is to assess <baseline> and <target> models that convert spoken language transcripts into well-structured, information-dense written text.
</role>
<task>
You will be given:
1. <transcript> in a format "text【0】text【1】... text 【2】". Where each【number】is a <marker> and goes AFTER the text it references. Markers are zero-based and are in sequential order.
2. <baseline> output of baseline that was reviewed by humans and certified by original speakers. The output is a series well-structured <paragraphs>, each paragraph is enclosed into <p></p>.
3. <target> output produced by the model you are evaluating. The output is a series well-structured <paragraphs>, each paragraph is enclosed into <p></p>.

Follow the guidelines in <evaluation> to evaluate the performance of the <baseline> and <target> models and generate a <final_report> that contains:
1. <suggested_model> based on the evaluation results: BASELINE if <baseline> is better, TARGET if <target> is better, or BOTH if both are nearly-equally good.
2. <evaluation_results> comparing <baseline> and <target> in terms of the four axes of evaluation.
</task>

<evaluation>
To comprehensively evaluate the performance of these models, you must assess them along the following four statistically independent axes on an integer scale of 1 to 10:

1. Information Preservation: The extent to which the model accurately captures and conveys all the essential information present in the transcript without omission or distortion. Pay special attention to facts, numbers, named entities, and other important information.
2. Coherence and Structure: The logical flow, organization, and clarity of the generated text, ensuring that it follows a coherent narrative or argument and is appropriately structured for the chosen format.
3. Timestamp Integrity: The accurate and complete inclusion of the special markers 【number】 in the output, preserving the temporal structure of the original transcript.
</evaluation>
"""

    prompt = f"""
<transcript>{transcript}</transcript>
<target>{target}</target>
<baseline>{baseline}</baseline>
""".strip()

    response = model.prompt_model(
        messages=[
            User(content=prompt),
            Assistant(content="<final_report><suggested_model>"),
        ],
        temperature=0.3,
        system=system_prompt,
    )
    assert isinstance(response, str)
    final_report_raw = "<final_report><suggested_model>" + response

    return final_report_raw


def test_eval_get_paragraphs() -> None:
    with open("samples/obama.json") as f:
        content = Content(**json.load(f))

    baseline = "\n".join(f"<p>{p}</p>" for p in content.passages)
    baseline = f"<paragraphs>{baseline}</paragraphs>"

    llm = plato.llm.get_model("anthropic/claude-3-5-sonnet")
    text = plato.ops.render({i: t.text for i, t in enumerate(content.transcript)})
    target = "\n".join(
        f"<p>{p}</p>"
        for p in plato.get_paragraphs(
            text, llm, max_tokens=4096, temperature=0.5, chunk_size=2048
        )
    )
    target = f"<paragraphs>{target}</paragraphs>"

    result = evaluate(
        render({i: t.text for i, t in enumerate(content.transcript)}), baseline, target
    )

    match = re.search(r"<suggested_model>(.*?)</suggested_model>", result, re.DOTALL)
    assert match is not None
    result = match.group(1)
    assert result == "TARGET"
