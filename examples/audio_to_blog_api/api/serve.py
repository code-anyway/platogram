from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from synthesize import summarize_audio, prompt_content
from response import content_to_html


app = FastAPI()


def get_src(
        url: str | None = Form(None),
        file: UploadFile | None = File(None)
) -> Form(...) | File(...):
    if file is not None:
        src = file.file
    elif url is not None:
        src = url
    else:
        raise HTTPException(status_code=400, detail="No URL or file found in request")
    return src


@app.get("/")
async def home() -> HTMLResponse:
    try:
        response = """
        <h1>This is the API for platogram's audio-to-blog</h1>
        <p>Given an HTTP POST request with an audio file (or link to one), get an HTML/Markdown blog post</p>
        <p>Use endpoint /post for post creation. Attach application/json for a url or a file.</p>
        <p>Use endpoint /query/{post_id} to add/revise a blog post given a query</p>
        """
        return HTMLResponse(content=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/post")
async def generate_post(
        url: str | None = Form(None),
        file: UploadFile | None = File(None)
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
        url: str | None = Form(None),
        file: UploadFile | None = File(None),
        prompt: str | None = Form(None)
) -> dict:
    try:
        src = get_src(url, file)

        response = prompt_content(url, prompt)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
