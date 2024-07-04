from flask import Flask, jsonify, request, Response, render_template_string
from typing import Tuple
from synthesize import summarize_audio
from response import content_to_html


app = Flask(__name__)


@app.route("/")
def home() -> Tuple[Response, int]:
    try:
        response = """<h1>This is the api for platogram's audio-to-blog</h1>
<p>Given an HTTP POST request with an audio file (or link to one), get an HTML/Markdown blog post</p>
<p>Use endpoint /post for post creation. Attatch application/json for a url or a file.</p>
<p>Use endpoint /query/post_id to add/revise a blog post given a query</p>"""

        return render_template_string(response), 200
    except Exception as e:
        return jsonify({"error": e}), 500


@app.route("/post", methods=["POST"])
def post() -> Tuple[Response, int]:
    data = request.get_json()
    files = request.files

    if "url" in data:
        src = data["url"]
    elif "file" in files:
        src = files["file"]
    else:
        return jsonify({"error": "No URL or file found in request"}), 400

    content = summarize_audio(src)

    file_name, content = content_to_html(content)

    response = {"html": content, "post_id": file_name}

    return jsonify(response), 200


@app.route("/query/<int:post_id>", methods=["POST"])
def refine_post(post_id: int, query: str) -> Tuple[Response, int]:
    ...
