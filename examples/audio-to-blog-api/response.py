from platogram import Content, SpeechEvent

def content_to_html(index: Content) -> str:
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
    
    for chunk in transcript:
        timestamp = format_time(chunk.time_ms)

        html += f"""
           <h8>time: {timestamp}</h7>
           <h6>{chunk.text}</h6>
       """

    html += "</details>"

    return html

def format_time(time_ms: str) -> str:
    time_seconds = time_ms // 1000
    time_minutes = time_seconds // 60
    time_hours = time_minutes // 60

    if time_hours == 0:
        return f"{time_minutes%60}:{time_seconds%60}"
    else:
        return f"{time_hours}:{time_minutes%60}:{time_seconds%60}"
