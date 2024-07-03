import hashlib
import re
import logging
from datetime import datetime


logger = logging.getLogger(__name__)


def make_filesystem_safe(s):
    # Remove leading and trailing whitespace
    s = s.strip()
    # Replace spaces with underscores
    s = s.replace(" ", "_")
    # Remove or replace invalid characters
    s = re.sub(r"[^\w\-\.]", "", s)
    # Optional: truncate the string to a max length, e.g., 255 characters
    return s[:255]


def get_sha256_hash(data):
    """Generate a sha256 hash for a given data."""
    sha256 = hashlib.sha256()
    sha256.update(data.encode())
    return sha256.hexdigest()


def parse_hh_mm_ss(s: str) -> int:
    if s.count(":") == 1:
        s = "00:" + s
    elif s.count(":") == 2:
        pass
    else:
        raise ValueError(f"Invalid time format: {s}")

    if s.find(".") == -1:
        timestamp, after_dot = (s.replace(" ", ""), "0")
    else:
        timestamp, after_dot = s.replace(" ", "").split(".", 1)

    t = datetime.strptime(timestamp, "%H:%M:%S")
    extra_micros = int(after_dot[:6].ljust(6, "0"))
    return (
        t.hour * 60 * 60 * 1_000
        + t.minute * 60 * 1_000
        + t.second * 1_000
        + t.microsecond // 1_000
        + extra_micros // 1_000
    )


def format_time(time_ms: int) -> str:
    hours, remainder = divmod(time_ms, 3600000)
    minutes, seconds = divmod(remainder, 60000)
    seconds, milliseconds = divmod(seconds, 1000)
    if hours > 0:
        return f"{hours}:{minutes:02}:{seconds:02}"
    else:
        return f"{minutes:02}:{seconds:02}"
