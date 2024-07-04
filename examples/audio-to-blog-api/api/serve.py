from flask import Flask, request, jsonify, Response
from typing import Tuple
from synthesis import summarize_audio
from response import content_to_html

app = Flask(__name__)
    with open(f"posts/{post_id}", "r") as post_body:
        body = post_body.read()


@app.route("/")
def home() -> Tuple[Response, int]:
    try:
        response = {"body": """<h1>This is the api for platogram's audio-to-blog</h1>
            <p>Given an HTTP POST request with an audio file (or link to one), get an HTML/Markdown blog post</p>
            <p>Use endpoint /post for post creation</p>
            <p>Use endpoint /query/post_id to add/revise a blog post given a query</p>
        """}
        return jsonify(response), 500
    except Exception as e:
        return jsonify({"error": e}), 500


@app.route("/post", methods=["POST"])
def post() -> str:
    req = request.json
    
    return body

@app.route("/query/<int:post_id>", methods=["POST"])
def refine_post(post_id: int, query: str) -> Tuple[Response, int]:
    try:
        data = request.json
        return jsonify({}), 200

    except Exception as e:
        return jsonify({"error": e}), 500
