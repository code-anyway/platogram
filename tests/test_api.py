import asyncio
import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ["PLATOGRAM_ROOT"] = temp_dir
        from platogram.api_main import app  # type: ignore

        with TestClient(app) as c:
            yield c


@pytest.mark.skip("Skipping REST API Test")
def test_add_content(client):
    response = client.post(
        "/content",
        json={
            "url": "https://www.youtube.com/shorts/xJwkj25fFK4",
            "transcribe": True,
            "collection": "shorts",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"id": "xJwkj25fFK4"}

    response = client.get("/content/xJwkj25fFK4")
    assert response.status_code == 200
    content = response.json()
    assert content["id"] == "xJwkj25fFK4"
    assert content["status"] == "queued"


async def wait_for_content_ready(client, content_id, timeout=120):
    start_time = asyncio.get_event_loop().time()
    while True:
        response = client.get(f"/content/{content_id}")
        assert response.status_code == 200
        content = response.json()
        if content["status"] == "ready":
            return

        if asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError(
                f"Content {content_id} not ready after {timeout} seconds"
            )

        await asyncio.sleep(0.5)


@pytest.mark.skip("Skipping REST API Test")
@pytest.mark.asyncio
async def test_add_content_and_wait_for_ready(client):
    response = client.post(
        "/content",
        json={
            "url": "https://api.waffly.factory.codes/api/audio/show/mV3Zrv3k",
            "transcribe": True,
            "collection": "shorts",
        },
    )
    assert response.status_code == 200
    content_id = response.json()["id"]

    await wait_for_content_ready(client, content_id)

    response = client.get(
        "/content/https://api.waffly.factory.codes/api/audio/show/mV3Zrv3k"
    )
    assert response.status_code == 200
    content = response.json()
    assert content["status"] == "ready"

    response = client.get(
        "/content/https://api.waffly.factory.codes/api/audio/show/mV3Zrv3k"
    )
    assert response.status_code == 200
    content = response.json()
    assert content["status"] == "ready"


@pytest.mark.skip("Skipping REST API Test")
def test_add_content_missing_url(client):
    response = client.post(
        "/content", json={"transcribe": True, "collection": "shorts"}
    )
    assert response.status_code == 422


@pytest.mark.skip("Skipping REST API Test")
def test_retrieve_nonexistent_content(client):
    response = client.get("/content/nonexistent")
    assert response.status_code == 404


@pytest.mark.skip("Skipping REST API Test")
@pytest.mark.asyncio
async def test_generate_responses(client):
    response = client.post(
        "/content",
        json={
            "url": "https://api.waffly.factory.codes/api/audio/show/mV3Zrv3k",
            "transcribe": False,
            "collection": "shorts",
        },
    )
    assert response.status_code == 200
    content_id = response.json()["id"]

    await wait_for_content_ready(client, content_id)

    response = client.get(
        "/content/https://api.waffly.factory.codes/api/audio/show/mV3Zrv3k"
    )
    assert response.status_code == 200
    content = response.json()
    assert content["status"] == "ready"

    response = client.post(
        "/generate",
        json={
            "scope": [
                {
                    "id": "https://api.waffly.factory.codes/api/audio/show/mV3Zrv3k",
                    "spans": [],
                }
            ],
            "collection": "shorts",
            "prompt": "Summarize and translate to Spanish.",
        },
    )
    assert response.status_code == 200
    response = response.text
    assert response


@pytest.mark.skip("Skipping REST API Test")
def test_generate_responses_empty_ids(client):
    response = client.post(
        "/generate",
        json={"scope": [], "prompt": "Explain this to a 5-year-old in Spanish."},
    )
    assert response.status_code == 422


@pytest.mark.skip("Skipping REST API Test")
def test_generate_responses_missing_prompt(client):
    response = client.post(
        "/generate",
        json={
            "scope": [
                {"id": "https://www.youtube.com/shorts/xJwkj25fFK4", "intervals_ms": []}
            ]
        },
    )
    assert response.status_code == 422
