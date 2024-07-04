from platogram import Content, User


def format_time(ms):
    seconds = ms // 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def content_to_html(content: Content) -> str:
    file_name, index = content

    html = f"""
        <h2>{index.title}</h2>
        <h4>{index.summary}</h4>
    """

    for paragraph in index.paragraphs:
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

    return html
