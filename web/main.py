import asyncio
import base64
import os
import re
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4

import httpx
import jwt
import logfire
import stripe
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

import platogram as plato

SCOPES = [
    "https://mail.google.com/",
]


logfire.configure()
app = FastAPI()


class RedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.hostname == "platogram.ai":
            return RedirectResponse(
                url=str(request.url).replace("platogram.ai", "web.platogram.ai"),
                status_code=301,
            )
        return await call_next(request)


app.add_middleware(RedirectMiddleware)

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
    price: Optional[float] = None
    token: Optional[str] = None


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
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_token_and_get_user_id),
    file: Optional[UploadFile] = File(None),
    payload: Optional[str] = Form(None),
    lang: Optional[Language] = Form(None),
    price: Optional[float] = Form(None),
    token: Optional[str] = Form(None),
):
    if not lang:
        lang = "en"

    if user_id in tasks and tasks[user_id].status == "running":
        raise HTTPException(status_code=400, detail="Conversion already in progress")

    if payload is None and file is None:
        raise HTTPException(
            status_code=400, detail="Either payload or file must be provided"
        )

    if payload is not None:
        request = ConversionRequest(payload=payload, lang=lang, price=price, token=token)
    else:
        # Create a named temporary directory if it doesn't exist
        tmpdir = Path(tempfile.gettempdir()) / "platogram_uploads"
        tmpdir.mkdir(parents=True, exist_ok=True)
        file_ext = file.filename.split(".")[-1]
        temp_file = Path(tmpdir) / f"{uuid4()}.{file_ext}"
        file_content = await file.read()
        with open(temp_file, "wb") as fd:
            fd.write(file_content)
            fd.close()

        request = ConversionRequest(payload=f"file://{temp_file}", lang=lang)

    tasks[user_id] = Task(start_time=datetime.now(), request=request, price=price, token=token)
    background_tasks.add_task(convert_and_send_with_error_handling, request, user_id)
    return {"message": "Conversion started"}


@app.get("/status")
async def status(user_id: str = Depends(verify_token_and_get_user_id)) -> dict:
    if user_id not in tasks:
        return {"status": "idle"}
    if tasks[user_id].status == "running":
        return {"status": "running"}
    if tasks[user_id].status == "failed":
        return {"status": "failed", "error": tasks[user_id].error}
    if tasks[user_id].status == "done":
        return {"status": "done"}
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


async def audio_to_paper(
    url: str, lang: Language, output_dir: Path, user_id: str
) -> tuple[str, str]:
    # Get absolute path of current working directory
    script_path = Path.cwd() / "examples" / "audio_to_paper.sh"
    command = f'cd {output_dir} && {script_path} "{url}" --lang {lang} --verbose'

    if user_id in processes:
        raise RuntimeError("Conversion already in progress.")

    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        shell=True,
    )
    processes[user_id] = process

    try:
        stdout, stderr = await process.communicate()
    finally:
        if user_id in processes:
            del processes[user_id]

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
        await loop.run_in_executor(pool, _send_email_sync, user_id, subj, body, files)


async def convert_and_send_with_error_handling(
    request: ConversionRequest, user_id: str
):
    try:
        await convert_and_send(request, user_id)
        tasks[user_id].status = "done"
        if request.token and request.token.lower() != 'null':
            stripe.api_key = os.getenv("STRIPE_API_KEY")
            charge = stripe.Charge.create(
                amount=int(float(request.price) * 100),
                currency='usd',
                source=request.token,
                description='Platogram audio to paper conversion'
            )
            logfire.info("Charge successful", price=request.price, user_id=user_id, charge_id=charge.id)
        else:
            logfire.info(f"No charge for user {user_id}", user_id=user_id)
    except Exception as e:
        logfire.exception(f"Error in background task for user {user_id}: {str(e)}")

        error = str(e)
        # Truncate and simplify error message for user-friendly display
        model = plato.llm.get_model("anthropic/claude-3-5-sonnet", key=os.getenv("ANTHROPIC_API_KEY"))
        error = model.prompt_model(messages=[
            plato.types.User(
                content=f"""
                Given the following error message, provide a concise, user-friendly explanation 
                that focuses on the key issue and any actionable steps. Avoid technical jargon 
                and keep the message under 256 characters:

                Error: {error}
                """
            )
        ])

        error = error.strip()  # Remove any leading/trailing whitespace
        tasks[user_id].error = error
        tasks[user_id].status = "failed"


async def convert_and_send(request: ConversionRequest, user_id: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        if not (
            request.payload.startswith("http")
            or request.payload.startswith("file:///tmp/platogram_uploads")
        ):
            raise HTTPException(status_code=400, detail="Please provide a valid URL.")
        else:
            url = request.payload

        try:
            stdout, stderr = await audio_to_paper(
                url, request.lang, Path(tmpdir), user_id
            )
        finally:
            if request.payload.startswith("file:///tmp/platogram_uploads"):
                try:
                    os.remove(
                        request.payload.replace(
                            "file:///tmp/platogram_uploads", "/tmp/platogram_uploads"
                        )
                    )
                except OSError as e:
                    logfire.warning(
                        f"Failed to delete temporary file {request.payload}: {e}"
                    )

        title_match = re.search(r"<title>(.*?)</title>", stdout, re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
        else:
            title = "👋"
            logfire.warning("No title found in stdout, using default title")

        abstract_match = re.search(r"<abstract>(.*?)</abstract>", stdout, re.DOTALL)
        if abstract_match:
            abstract = abstract_match.group(1).strip()
        else:
            abstract = ""
            logfire.warning("No abstract found in stdout, using default abstract")

        files = [f for f in Path(tmpdir).glob("*no-refs.pdf") if f.is_file()]

        subject = f"[Platogram] {title}"
        body = f"""Hi there!

Platogram transformed spoken words into document you can read and enjoy, or attach to ChatGPT/Claude/etc and prompt!

{abstract}

Please reply to this e-mail if any suggestions, feedback, or questions.

---
Support Platogram by donating here: https://buy.stripe.com/eVa29p3PK5OXbq84gl
Suggested donation: $2 per hour of content converted."""

        await send_email(user_id, subject, body, files)


def _send_email_sync(user_id: str, subj: str, body: str, files: list[Path]):
    creds = get_gmail_service()

    service = build("gmail", "v1", credentials=creds)

    msg = MIMEMultipart()
    msg["From"] = os.getenv("PLATOGRAM_EMAIL_FROM")
    msg["To"] = user_id
    msg["Subject"] = subj

    msg.attach(MIMEText(body, "plain"))

    # Attach files if provided
    for file in files:
        with open(file, "rb") as file:
            file_name = file.name.split("/")[-1]
            part = MIMEApplication(file.read(), Name=file_name)
        part["Content-Disposition"] = f'attachment; filename="{file_name}"'
        msg.attach(part)

    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    message_body = {"raw": raw_message}

    sent_message = send_with_retry(service, message_body)

    delete_with_retry(service, sent_message["id"])


def send_with_retry(service, message_body, max_retries=5, initial_delay=1):
    for attempt in range(max_retries):
        try:
            return service.users().messages().send(userId="me", body=message_body).execute()
        except HttpError as error:
            if error.resp.status in [500, 503]:  # Internal Server Error or Service Unavailable
                delay = initial_delay * (2 ** attempt)
                time.sleep(delay)
            else:
                raise error


def delete_with_retry(service, message_id, max_retries=5, initial_delay=1):
    for attempt in range(max_retries):
        try:
            service.users().messages().delete(userId="me", id=message_id).execute()
            return
        except HttpError as error:
            if error.resp.status in [500, 503]:  # Internal Server Error or Service Unavailable
                delay = initial_delay * (2 ** attempt)
                time.sleep(delay)
            else:
                raise error


def get_gmail_service():
    credentials = service_account.Credentials.from_service_account_file(
        ".id/google-service-account.json", scopes=SCOPES)
    user_email = os.getenv("PLATOGRAM_USER_EMAIL")
    delegated_credentials = credentials.with_subject(user_email)

    return delegated_credentials


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
