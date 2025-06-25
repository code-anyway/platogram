import os
import shutil
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from typing import Optional
from platogram.types import SpeechEvent


def convert_to_wav(file: Path, output_dir: Path) -> Path:
    """
    Converts an audio or video file to WAV format using ffmpeg.
    
    Args:
        file: Path to the input file.
        output_dir: Directory to save the converted file.
    
    Returns:
        Path to the converted WAV file.
    """
    if not file.exists():
        raise FileNotFoundError(f"The file {file} does not exist.")
    
    output_file = output_dir / f"{file.stem}.wav"
    
    command = [
        "ffmpeg",
        "-i", str(file),
        "-ar", "16000",  # 16kHz sample rate (optimal for Whisper)
        "-ac", "1",      # mono
        "-c:a", "pcm_s16le",  # 16-bit PCM encoding
        str(output_file),
        "-y"  # overwrite output file if it exists
    ]
    
    try:
        subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"An error occurred while converting {file} to WAV: {e}. "
            f"stderr: {e.stderr.decode('utf-8')}"
        )
    
    return output_file


class Model:
    def __init__(self, model_size: str = "large-v3"):
        """
        Initialize Whisper model using whisper.cpp CLI optimized for Mac M4.
        
        Args:
            model_size: Size of the model (tiny, base, small, medium, large, large-v2, large-v3)
        """
        self.model_size = model_size
        
        # Check if whisper-cli is available
        if not shutil.which("whisper-cli"):
            raise RuntimeError(
                "whisper-cli not found. Please install whisper.cpp: brew install whisper-cpp"
            )
        
        # Set up model path
        self.model_path = self._get_model_path(model_size)
        
        # Download model if not exists
        self._ensure_model_exists()
    
    def _get_model_path(self, model_size: str) -> Path:
        """Get the path to the model file"""
        # Use project-local models directory
        models_dir = Path("whisper-models")
        models_dir.mkdir(exist_ok=True)
        
        # Map model sizes to filenames
        model_files = {
            "tiny": "ggml-tiny.bin",
            "tiny.en": "ggml-tiny.en.bin", 
            "base": "ggml-base.bin",
            "base.en": "ggml-base.en.bin",
            "small": "ggml-small.bin",
            "small.en": "ggml-small.en.bin",
            "medium": "ggml-medium.bin",
            "medium.en": "ggml-medium.en.bin",
            "large": "ggml-large.bin",
            "large-v1": "ggml-large-v1.bin",
            "large-v2": "ggml-large-v2.bin",
            "large-v3": "ggml-large-v3.bin",
        }
        
        filename = model_files.get(model_size, f"ggml-{model_size}.bin")
        return models_dir / filename
    
    def _ensure_model_exists(self):
        """Download model if it doesn't exist"""
        if self.model_path.exists():
            return
        
        # Map to download URLs
        base_url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
        
        try:
            subprocess.run([
                "curl", "-L", f"{base_url}/{self.model_path.name}", 
                "-o", str(self.model_path)
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to download model {self.model_path.name}: {e}")
    
    def transcribe(self, file: Path, lang: Optional[str] = None) -> list[SpeechEvent]:
        """
        Transcribe audio file and return speech events with timestamps using whisper.cpp VTT output.
        
        Args:
            file: Path to audio file
            lang: Language code (e.g., "en", "es", "fr")
        
        Returns:
            List of SpeechEvent objects with timestamps and text
        """
        from platogram.parsers import parse_vtt
        
        with TemporaryDirectory() as temp_dir:
            # Convert to WAV if needed (whisper.cpp has issues with some formats like MOV)
            if not str(file).lower().endswith(('.wav', '.flac')):
                print(f"Converting {file} to WAV format...")
                file = convert_to_wav(file, Path(temp_dir))
                print(f"Converted to: {file}")
            
            # Build whisper-cli command to output VTT
            cmd = [
                "whisper-cli",
                "-m", str(self.model_path.absolute()),
                "-f", str(file.absolute()),
                "--output-vtt",
                "-of", str(Path(temp_dir) / "output")
            ]
            
            # Add language if specified
            if lang:
                cmd.extend(["-l", lang])
            
            # Run whisper-cli
            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"whisper-cli failed: {e.stderr}")
            
            # Parse VTT file using existing parser
            vtt_file = Path(temp_dir) / "output.vtt"
            if not vtt_file.exists():
                raise RuntimeError("whisper-cli did not produce VTT output")
            
            return parse_vtt(vtt_file.read_text())
    
    def save_vtt(self, file: Path, lang: Optional[str] = None, output_path: Optional[Path] = None) -> Path:
        """
        Transcribe audio and save as VTT file using whisper.cpp.
        
        Args:
            file: Path to audio file
            lang: Language code
            output_path: Path to save VTT file (defaults to audio filename with .vtt extension)
        
        Returns:
            Path to the saved VTT file
        """
        if output_path is None:
            output_path = file.with_suffix('.vtt')
        
        # Build whisper-cli command with VTT output
        cmd = [
            "whisper-cli",
            "-m", str(self.model_path),
            "-f", str(file),
            "--output-vtt",
            "-of", str(output_path.with_suffix(''))  # whisper-cli adds .vtt extension
        ]
        
        # Add language if specified
        if lang:
            cmd.extend(["-l", lang])
        
        # Run whisper-cli
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"whisper-cli VTT generation failed: {e.stderr}")
        
        return output_path