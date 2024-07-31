from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from tempfile import TemporaryDirectory
import uuid
import subprocess
from fastapi import BackgroundTasks
import os
import zipfile
import shutil
from fastapi.responses import FileResponse
import time

app = FastAPI()

app.mount("/static", StaticFiles(directory="examples"), name="static")

@app.get("/")
async def serve_html():
    with open("examples/remember.html", "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content, status_code=200)

@app.post("/doc")
async def upload_doc(audio: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    contents = await audio.read()
    job_id = str(uuid.uuid4())[:8]
    
    def process_audio(contents):
        with TemporaryDirectory() as temp_dir:
            with open(f"{temp_dir}/audio.webm", "wb") as f:
                f.write(contents)
                
            subprocess.run([f"{os.path.dirname(os.path.abspath(__file__))}/audio_to_paper.sh", f"file://{temp_dir}/audio.webm"], cwd=temp_dir)

            time.sleep(30)

            # Get all .md, .docx, and .pdf files in the current directory
            files_to_zip = [file for file in os.listdir(temp_dir) if file.endswith((".md", ".docx", ".pdf"))]

            if files_to_zip:
                # Get the name of the first file (without extension) for the zip file name
                zip_file_name = os.path.splitext(files_to_zip[0])[0] + ".zip"

                # Create a zip file named after the first file
                with zipfile.ZipFile(f"{temp_dir}/{zip_file_name}", "w") as zip_file:
                    for file in files_to_zip:
                        zip_file.write(os.path.join(temp_dir, file), file)

                # create job_id directory if it doesn't exist
                if not os.path.exists(f"content/{job_id}"):
                    os.makedirs(f"content/{job_id}")

                # copy zip file to content directory
                shutil.copy(f"{temp_dir}/{zip_file_name}", f"content/{job_id}/{zip_file_name}")
    
    background_tasks.add_task(process_audio, contents)

    return {"job_id": job_id}

@app.get("/content/{job_id}")
async def get_content(job_id: str):
    zip_file_path = os.path.join(f"content/{job_id}", os.listdir(f"content/{job_id}")[0])
    return FileResponse(zip_file_path)

@app.get("/jobs/{job_id}")
async def get_status(job_id: str):
    if os.path.exists(f"content/{job_id}"):
        return {"status": "completed", "url": f"/content/{job_id}"}
    else:
        return {"status": "pending"}
