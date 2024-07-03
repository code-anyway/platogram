from flask import Flask, request, jsonify, Response
from typing import Tuple
from synthesis import summarize_audio
from response import content_to_html

app = Flask(__name__)
    with open(f"posts/{post_id}", "r") as post_body:
        body = post_body.read()


@app.route("/")
def home() -> str:
    body = """<h1>Meeting to Blog!</h1>
        <h3>Powered by Platogram (https://github.com/code-anyway/platogram)</h3>
        <p>Given an audio recording (of a meeting), generate a blog post</p>
    """
    return body

@app.route("/post", methods=["POST"])
def post() -> str:

    return body

@app.route("/query/<int:post_id>", methods=["POST"])
def refine_post(post_id: int, query: str) -> Tuple[Response, int]:
    try:
        data = request.json
        return jsonify({}), 200

    except Exception as e:
        return jsonify({"error": e}), 500
