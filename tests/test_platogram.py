import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import web.main as web_main
from web.main import (
    ConversionRequest,
    audio_to_paper,
    convert_and_send_with_error_handling,
    send_email,
    Task,
)


@pytest.mark.asyncio
async def test_audio_to_paper():
    url = "https://www.youtube.com/shorts/rjVY7HXN6qA"
    lang = "en"
    with tempfile.TemporaryDirectory() as tmpdir:
        stdout, stderr = await audio_to_paper(url, lang, Path(tmpdir), "artyom@codeanyway.com")

        output_files = list(Path(tmpdir).glob('*'))
        pdf_files = [f for f in output_files if f.suffix == '.pdf']
        assert len(pdf_files) == 2, f"Expected 2 .pdf files, but found {len(pdf_files)}.\n\n{stdout}\n\n{stderr}"


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
    web_main.tasks[user_id] = Task(start_time=datetime.now(), request=request, status="running")
    await convert_and_send_with_error_handling(request, user_id)
