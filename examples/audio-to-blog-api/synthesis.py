import platogram as plato
import os

def summarize_audio(url: str, anthropic_model: str = "claude-3-5-sonnet", assembly_ai_model: str = "best") -> plato.Content:
    key = os.environ["ANTHROPIC_API_KEY"]
    llm = plato.llm.get_model(anthropic_model, os.environ["ANTHROPIC_API_KEY"])
    asr = plato.asr.get_model(assembly_ai_model,os.environ["ASSEMBLYAI_API_KEY"])

    transcript = plato.extract_transcript(url, asr)
    content = plato.index(transcript, llm)

    return content
