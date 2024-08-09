import asyncio
import os
import smtplib
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Literal, Optional

import httpx
import jwt
import logfire
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

logfire.configure()
app = FastAPI()


AUTH0_DOMAIN = "dev-df8axtz2fh7qc2n2.us.auth0.com"
API_AUDIENCE = "https://web.platogram.ai"
ALGORITHMS = ["RS256"]
JWKS_URL = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"


tasks = {}
processes = {}
Language = Literal["en", "es"]


class ConversionRequest(BaseModel):
    payload: str
    lang: Language = "en"


class Task(BaseModel):
    start_time: datetime
    request: ConversionRequest
    status: Literal["running", "done", "failed"] = "running"
    error: Optional[str] = None


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Cache for the Auth0 public key
auth0_public_key_cache = {
    "key": None,
    "last_updated": 0,
    "expires_in": 3600,  # Cache expiration time in seconds (1 hour)
}


@app.get("/")
async def index():
    return FileResponse("web/index.html")


async def get_auth0_public_key():
    current_time = time.time()

    # Check if the cached key is still valid
    if (
        auth0_public_key_cache["key"]
        and current_time - auth0_public_key_cache["last_updated"]
        < auth0_public_key_cache["expires_in"]
    ):
        return auth0_public_key_cache["key"]

    # If not, fetch the JWKS from Auth0
    async with httpx.AsyncClient() as client:
        response = await client.get(JWKS_URL)
        response.raise_for_status()
        jwks = response.json()

    x5c = jwks["keys"][0]["x5c"][0]

    # Convert the X.509 certificate to a public key
    cert = load_pem_x509_certificate(
        f"-----BEGIN CERTIFICATE-----\n{x5c}\n-----END CERTIFICATE-----".encode()
    )
    public_key = cert.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Update the cache
    auth0_public_key_cache["key"] = public_key
    auth0_public_key_cache["last_updated"] = current_time

    return public_key


async def verify_token_and_get_user_id(token: str = Depends(oauth2_scheme)):
    try:
        public_key = await get_auth0_public_key()
        payload = jwt.decode(
            token,
            key=public_key,
            algorithms=ALGORITHMS,
            audience=API_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/",
        )
        return payload["platogram:user_email"]
    except Exception as e:
        raise HTTPException(status_code=401, detail="Couldn't verify token") from e


@app.post("/convert")
@logfire.instrument()
async def convert(
    request: ConversionRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_token_and_get_user_id),
):
    if user_id in tasks:
        raise HTTPException(status_code=400, detail="Conversion already in progress")

    tasks[user_id] = Task(start_time=datetime.now(), request=request)
    background_tasks.add_task(convert_and_send_with_error_handling, request, user_id)
    return {"message": "Conversion started"}


@app.get("/status")
async def status(user_id: str = Depends(verify_token_and_get_user_id)) -> dict:
    if user_id not in tasks:
        return {"status": "idle"}
    if tasks[user_id].status == "running":
        return {"status": "busy"}
    if tasks[user_id].status == "failed":
        return {"status": "failed", "error": tasks[user_id].error}
    return {"status": "idle"}


@app.get("/reset")
@logfire.instrument()
async def reset(user_id: str = Depends(verify_token_and_get_user_id)):
    if user_id in processes:
        processes[user_id].terminate()
        del processes[user_id]

    if user_id in tasks:
        del tasks[user_id]

    return {"message": "Session reset"}


async def audio_to_paper(url: str, lang: Language, output_dir: Path, user_id: str) -> tuple[str, str]:
    # Get absolute path of current working directory
    script_path = Path.cwd() / "examples" / "audio_to_paper.sh"
    command = f"cd {output_dir} && {script_path} {url} --lang {lang}"

    if user_id in processes:
        raise RuntimeError("Conversion already in progress.")

    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        shell=True
    )
    processes[user_id] = process
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"""Failed to execute {command} with return code {process.returncode}.

stdout:
{stdout.decode()}

stderr:
{stderr.decode()}""")

    return stdout.decode(), stderr.decode()


async def send_email(user_id: str, subj: str, body: str, files: list[Path]):
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor() as pool:
        await loop.run_in_executor(
            pool, _send_email_sync, user_id, subj, body, files
        )


async def convert_and_send_with_error_handling(request: ConversionRequest, user_id: str):
    try:
        await convert_and_send(request, user_id)
        tasks[user_id].status = "done"
    except Exception as e:
        logfire.exception(f"Error in background task for user {user_id}: {str(e)}")

        if user_id in tasks:
            error = str(e)
            if len(error) > 256:
                error = "🤯🤯🤯"
            tasks[user_id].error = error
            tasks[user_id].status = "failed"


async def convert_and_send(request: ConversionRequest, user_id: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        if not request.payload.startswith("http"):
            raise HTTPException(status_code=400, detail="Please provide a valid URL.")
        else:
            url = request.payload

        stdout, stderr = await audio_to_paper(url, request.lang, Path(tmpdir), user_id)
        files = [f for f in Path(tmpdir).glob('*') if f.is_file()]
        await send_email(user_id, "Structured Documents from Platogram", "Here you are 💜", files)    


def _send_email_sync(user_id: str, subj: str, body: str, files: list[Path]):
    # Email configuration
    smtp_user = os.getenv("PLATOGRAM_SMTP_USER")
    smtp_server = os.getenv("PLATOGRAM_SMTP_SERVER")
    smtp_port = 587
    sender_password = os.getenv("PLATOGRAM_SMTP_PASSWORD")
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = os.getenv("PLATOGRAM_SMTP_FROM")
    msg['To'] = user_id
    msg['Subject'] = subj
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach files if provided
    for file in files:
        with open(file, "rb") as file:
            file_name = file.name.split("/")[-1]
            part = MIMEApplication(file.read(), Name=file_name)
        part['Content-Disposition'] = f'attachment; filename="{file_name}"'
        msg.attach(part)
    
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, sender_password)
        server.send_message(msg)


if __name__ == "__main__":
    import uvicorn


    uvicorn.run(app, host="0.0.0.0", port=8000)
