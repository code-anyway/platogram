from platogram import Content
from typing import Tuple

def content_to_html(content: Tuple[str, Content]) -> Tuple[str, str]:
    file_name, index = content

    html = f"""
        <h2>{index.title}</h2>
        <h4>{index.summary}</h4>
    """

    for paragraph in index.passages:
        html += f"<p>{paragraph}</p>"

    html += """
        <details>
        <summary>Expand for transcript</summary>
    """ 
    
    for chunk in index.transcript:
        timestamp = format_time(chunk.time_ms)

        html += f"""
           <h8>time: {timestamp}</h7>
           <h6>{chunk.text}</h6>
       """

    html += "</details>"

    return file_name, html

def format_time(time_ms: str) -> str:
    time_seconds = time_ms // 1000
    time_minutes = time_seconds // 60
    time_hours = time_minutes // 60

    if time_hours == 0:
        return f"{time_minutes%60}:{time_seconds%60}"
    else:
        return f"{time_hours}:{time_minutes%60}:{time_seconds%60}"
