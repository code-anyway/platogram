from flask import Flask, request, jsonify, Response
from typing import Tuple
from synthesize import summarize_audio
from response import content_to_html


app = Flask(__name__)


@app.route("/")
def home() -> Tuple[Response, int]:
    try:
        response = {
            "html": """<h1>This is the api for platogram's audio-to-blog</h1>
<p>Given an HTTP POST request with an audio file (or link to one), get an HTML/Markdown blog post</p>
<p>Use endpoint /post for post creation</p>
<p>Use endpoint /query/post_id to add/revise a blog post given a query</p>"""
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": e}), 500


@app.route("/post", methods=["POST"])
def post() -> Tuple[Response, int]:
    if "url" in data:=request.get_json():
        src = data["url"]
    elif "file" in request.files:
        src = request.files["file"]
    else:
        return jsonify({"error": "No URL or file found in request"}), 400

    content = summarize_audio(src)

    content = content_to_html(content)

    response = {"html": content, "post_id": "}

    return body, 200


@app.route("/query/<int:post_id>", methods=["POST"])
def refine_post(post_id: int, query: str) -> Tuple[Response, int]:
    try:
        data = request.json
        return jsonify({}), 200

    except Exception as e:
        return jsonify({"error": e}), 500
