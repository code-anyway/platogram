import tempfile
from pathlib import Path

import pytest

from web.main import ConversionRequest, audio_to_paper, convert_and_send, send_email


@pytest.mark.asyncio
async def test_audio_to_paper():
    url = "https://www.youtube.com/shorts/rjVY7HXN6qA"
    lang = "en"
    with tempfile.TemporaryDirectory() as tmpdir:
        stdout, stderr = await audio_to_paper(url, lang, Path(tmpdir))

        # Check if the expected files are present in the temporary directory
        output_files = list(Path(tmpdir).glob('*'))
        
        # Count the number of files for each extension
        md_files = [f for f in output_files if f.suffix == '.md']
        pdf_files = [f for f in output_files if f.suffix == '.pdf']
        docx_files = [f for f in output_files if f.suffix == '.docx']
        
        # Assert that there are exactly two files of each type
        assert len(md_files) == 2, f"Expected 2 .md files, but found {len(md_files)}"
        assert len(pdf_files) == 2, f"Expected 2 .pdf files, but found {len(pdf_files)}"
        assert len(docx_files) == 2, f"Expected 2 .docx files, but found {len(docx_files)}"


@pytest.mark.asyncio
async def test_send_email():
    files = [Path("samples/jfk.ogg")]
    user_id = "artyom.astafurov@gmail.com"
    subj = "Platogram Test"
    body = "Yo!"
    await send_email(user_id, subj, body, files)


@pytest.mark.asyncio
async def test_convert_and_send_http():
    request = ConversionRequest(payload="https://www.youtube.com/shorts/nXIHYB0Gp70", lang="en")
    user_id = "artyom.astafurov@gmail.com"
    await convert_and_send(request, user_id)