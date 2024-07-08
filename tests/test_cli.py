import os
from pathlib import Path
import tempfile
import platogram.cli as cli
from platogram.types import Content
import platogram as plato


def test_process_url():
    anthropic_api_key = os.environ["ANTHROPIC_API_KEY"]
    assemblyai_api_key = os.environ.get("ASSEMBLYAI_API_KEY")

    url = "https://www.youtube.com/shorts/XsLK3tPy9SI"

    with tempfile.TemporaryDirectory() as temp_dir:
        library = plato.library.get_semantic_local_chroma(Path(temp_dir))

        content = cli.process_url(
            url, library, anthropic_api_key, assemblyai_api_key, extract_images=True
        )

        assert isinstance(content, Content)
        assert content.title is not None
        assert content.summary is not None
        assert content.passages is not None
        assert content.transcript is not None
        assert content.images is not None

        assert content.transcript
        assert len(content.images) == len(content.transcript)
        assert all((library.home / image).exists() for image in content.images)
