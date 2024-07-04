from fastapi import FastAPI, HTTPException, Response, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from synthesize import summarize_audio
from response import content_to_html


app = FastAPI()


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
async def post(url: str | None = Form(None), file: UploadFile | None = File(None)) -> dict:
    try:
        if file is not None:
            src = file.file
        elif url is not None:
            src = url
        else:
            raise HTTPException(status_code=400, detail="No URL or file found in request")

        content = await summarize_audio(src)

        file_name, html_content = content_to_html(content)

        response = {"html": html_content, "post_id": file_name}
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/{post_id}")
async def refine_post(post_id: int, query: str) -> dict:
    try:
        return {"message": f"Refining post {post_id} with query: {query}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

