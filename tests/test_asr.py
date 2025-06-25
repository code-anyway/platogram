import platogram
from pathlib import Path
import pytest


def test_transcribe_assemblyai():
    transcript = platogram.asr.get_model("assembly-ai/best").transcribe(
        Path("samples/jfk.ogg")
    )
    assert "work must truly be our own" in transcript[-1].text


def test_transcribe_whisper_local():
    """Test local Whisper transcription"""
    if not Path("samples/jfk.ogg").exists():
        pytest.skip("Sample audio file not found")
    
    # Use tiny model for faster testing
    asr = platogram.asr.get_model("whisper-local/tiny")
    transcript = asr.transcribe(Path("samples/jfk.ogg"), lang="en")
    
    # Basic checks
    assert len(transcript) > 0, "Should produce at least one speech event"
    assert all(event.time_ms >= 0 for event in transcript), "All timestamps should be non-negative"
    assert all(len(event.text.strip()) > 0 for event in transcript), "All text should be non-empty"
    
    # Check that we get reasonable content (JFK speech contains these common words)
    full_text = " ".join(event.text for event in transcript).lower()
    assert any(word in full_text for word in ["and", "the", "to", "of"]), "Should contain common English words"


def test_whisper_vtt_export():
    """Test VTT file export functionality"""
    if not Path("samples/jfk.ogg").exists():
        pytest.skip("Sample audio file not found")
    
    asr = platogram.asr.get_model("whisper-local/tiny")
    
    # Test VTT export
    vtt_path = asr.save_vtt(Path("samples/jfk.ogg"), lang="en")
    
    assert vtt_path.exists(), "VTT file should be created"
    assert vtt_path.suffix == ".vtt", "Output should have .vtt extension"
    
    # Check VTT format
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    assert content.startswith("WEBVTT"), "VTT file should start with WEBVTT header"
    assert "-->" in content, "VTT file should contain timestamp markers"
    
    # Clean up
    vtt_path.unlink()
