import re

import platogram as plato


def test_quick_start() -> None:
    llm = plato.llm.get_model("anthropic/claude-3-5-sonnet")
    asr = plato.asr.get_model("assembly-ai/best")

    url = "https://www.youtube.com/shorts/XsLK3tPy9SI"
    doc = plato.extract_transcript(url, asr, lang="en")
    indexed_doc = plato.index(doc, llm)

    query = "Explain this to a 5 year old"
    response = llm.prompt(query, context=[indexed_doc], lang="en")

    assert re.findall(r"【\d+】", response)
