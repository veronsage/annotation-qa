import os
import tempfile

os.environ["AQA_DATA_DIR"] = tempfile.mkdtemp()
os.environ["AQA_API_KEY"] = "test-key"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app, headers={"X-API-Key": "test-key"})


def test_flow():
    pid = client.post("/projects", json={"name": "test"}).json()["id"]
    with open("samples/dataset.json", "rb") as a, open("samples/rules.json", "rb") as r:
        resp = client.post(f"/projects/{pid}/annotations", files={"annotations": a, "rules": r})
    assert resp.status_code == 200

    s = client.post(f"/projects/{pid}/analyze").json()
    assert s["items_total"] == 5
    assert s["items_flagged"] == 4

    q = client.get(f"/projects/{pid}/review-queue").json()
    assert q[0]["item_id"] == "img_004"


def test_no_key():
    anon = TestClient(app)
    assert anon.get("/projects").status_code == 401
    assert anon.get("/projects", headers={"X-API-Key": "wrong"}).status_code == 401
