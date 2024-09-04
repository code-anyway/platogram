import asyncio
import os
import re
import tempfile
from functools import partial
from pathlib import Path

import logfire
from telethon import TelegramClient, events

import platogram as plato

logfire.configure()


processes = {}
tasks = {}


async def handle_convert(client, event):
    sender = await event.get_sender()
    user_id = sender.id
    chat_id = event.chat_id

    if user_id in tasks:
        await client.send_message(chat_id, "Please wait for the previous task to complete.")
        return

    tmpdir = Path(tempfile.gettempdir()) / "platogram_uploads"
    tmpdir.mkdir(parents=True, exist_ok=True)

    if event.document:
        file = await event.download_media(file=tmpdir)
        url = f"file://{file}"
    else:
        url = event.text.strip()

    lang = "en"

    # Create and store the task for this user
    tasks[user_id] = asyncio.create_task(convert_and_respond_with_error_handling(client, url, lang, chat_id, user_id))


async def convert_and_respond_with_error_handling(client, url: str, lang: str | None, chat_id, user_id):
    try:
        await convert_and_respond(client, url, lang, chat_id, user_id)
    except Exception as e:
        error = str(e)
        # Truncate and simplify error message for user-friendly display
        model = plato.llm.get_model("anthropic/claude-3-5-sonnet", key=os.getenv("ANTHROPIC_API_KEY"))
        error = model.prompt_model(messages=[
            plato.types.User(
                content=f"""Given the following error message, provide a concise, user-friendly explanation 
that focuses on the key issue and any actionable steps. Avoid technical jargon 
and keep the message under 256 characters:

Error: {error}
"""
            )
        ])

        error = error.strip()  # Remove any leading/trailing whitespace

        await client.send_message(chat_id, f"{error}")
    finally:
        del tasks[user_id]


@logfire.instrument("convert_and_respond")
async def convert_and_respond(client, url: str, lang: str | None, chat_id, user_id):
    with tempfile.TemporaryDirectory() as tmpdir:
        if not (
            url.startswith("http")
            or url.startswith("file:///tmp/platogram_uploads")
        ):
            raise ValueError("Please provide a valid URL.")

        try:
            await client.send_message(chat_id, "Working on it... It takes about 5 minutes per 1 hour of content.")
            stdout, stderr = await audio_to_paper(url, lang, Path(tmpdir), user_id)
        finally:
            if url.startswith("file:///tmp/platogram_uploads"):
                try:
                    os.remove(
                        url.replace(
                            "file:///tmp/platogram_uploads", "/tmp/platogram_uploads"
                        )
                    )
                except OSError as e:
                    logfire.warning(
                        f"Failed to delete temporary file {url}: {e}"
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

        files = [f for f in Path(tmpdir).glob("*") if f.is_file()]

        for file in files:
            await client.send_file(chat_id, file)

        body = f"""{title}

{abstract}"""
        await client.send_message(chat_id, body)

        extra_message = """[Support Platogram by donating](https://buy.stripe.com/eVa29p3PK5OXbq84gl)"""
        await client.send_message(chat_id, extra_message, parse_mode="md")


async def audio_to_paper(
    url: str, lang: str, output_dir: Path, user_id: str
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


async def handle_other_messages(event):
    instructions = """
Welcome to Platogram! Here's how to use this bot:

1. Send or forward an audio file or a URL to an audio file.
2. I'll convert it to a readable document and send it back to you.

Supported formats:
- Audio files: MP3, WAV, M4A, OGG
- Video files: MP4, AVI, MOV
- URLs: YouTube, Vimeo, SoundCloud, and direct links to audio/video files

If you have any questions or need help, just type /start to see this message again.

Remember, your support helps keep Platogram running. Consider donating $2 per hour of converted content: https://buy.stripe.com/eVa29p3PK5OXbq84gl

Happy converting!
    """
    await event.reply(instructions)


def main():
    API_ID = os.getenv("TELEGRAM_API_ID")
    API_HASH = os.getenv("TELEGRAM_API_HASH")
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
    client.add_event_handler(partial(handle_convert, client), events.NewMessage(func=lambda e: e.document or e.text.strip().lower().startswith('http')))
    client.add_event_handler(handle_other_messages, events.NewMessage(pattern="/start"))
    client.run_until_disconnected()


if __name__ == "__main__":
    main()
