from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from response import content_to_html
from synthesize import summarize_audio, prompt_content
from tarfile import TarFile
from tempfile import SpooledTemporaryFile
from typing import List


app = FastAPI()


def get_src(
    urls: str | None = Form(None), files: UploadFile | None = File(None)
) -> List[str | SpooledTemporaryFile]:
    sources = []

    if files is not None:
        file_tar = TarFile(fileobj=files.file, mode="r")
        file_members = file_tar.getmembers()
        sources = [file_tar.extractfile(member) for member in file_members]
    if urls is not None:
        sources += [url for url in urls.split(",")]
    if sources == []:
        raise HTTPException(status_code=400, detail="No URL or file found in request")
    return sources


@app.get("/")
async def home() -> HTMLResponse:
    try:
        response = """
<h1>This is the API for platogram's audio-to-blog</h1>
<p>Given an HTTP POST request with an audio file (or link to one), get an HTML/Markdown blog post</p>
<p>Use endpoint /post for post creation. Attach application/json for a url or a file.</p>
<p>Use endpoint /query to create a blog post by querying an audio file</p>
"""
        return HTMLResponse(content=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/post")
async def generate_post(
    url: str | None = Form(None), file: UploadFile | None = File(None)
) -> dict:
    try:
        src = get_src(url, file)

        content = await summarize_audio(src)

        html_content = content_to_html(content)

        response = {"html": html_content}
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
async def refine_post(
    urls: str | None = Form(None),
    file: UploadFile | None = File(None),
    prompt: str = Form(...),
) -> dict:
    try:
        sources = get_src(urls, file)
        content = [await summarize_audio(src) for src in sources]

        response = await prompt_content(content, prompt)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
