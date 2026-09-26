import csv
import io
import json
import os
import secrets

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from app import qa, storage

API_KEY = os.environ.get("AQA_API_KEY")
if not API_KEY:
    API_KEY = secrets.token_urlsafe(16)
    print(f"AQA_API_KEY не задан, ключ на этот запуск: {API_KEY}")


def check_key(key: str = Depends(APIKeyHeader(name="X-API-Key", auto_error=False))):
    if key is None or not secrets.compare_digest(key, API_KEY):
        raise HTTPException(401, "bad api key")


app = FastAPI(title="Annotation QA", version="0.1.0")
storage.init_db()

STATIC = os.path.join(os.path.dirname(__file__), "static")


class NewProject(BaseModel):
    name: str


def check_project(pid):
    if not storage.project_exists(pid):
        raise HTTPException(404, "project not found")


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as f:
        return f.read()


@app.post("/projects", dependencies=[Depends(check_key)])
def new_project(p: NewProject):
    return {"id": storage.create_project(p.name)}


@app.get("/projects", dependencies=[Depends(check_key)])
def projects():
    return storage.get_projects()


# картинки датасета
@app.post("/projects/{pid}/items", dependencies=[Depends(check_key)])
async def upload_items(pid: str, files: list[UploadFile] = File(...)):
    check_project(pid)
    saved = []
    for f in files:
        name = os.path.basename(f.filename)
        with open(os.path.join(storage.project_dir(pid), name), "wb") as out:
            out.write(await f.read())
        saved.append(name)
    return {"saved": saved}


@app.get("/projects/{pid}/items/{name}", dependencies=[Depends(check_key)])
def get_item(pid: str, name: str):
    check_project(pid)
    path = os.path.join(storage.project_dir(pid), os.path.basename(name))
    if not os.path.isfile(path):
        raise HTTPException(404, "item not found")
    return FileResponse(path)


@app.post("/projects/{pid}/annotations", dependencies=[Depends(check_key)])
async def upload_annotations(pid: str, annotations: UploadFile = File(...), rules: UploadFile | None = File(None)):
    check_project(pid)
    data = json.loads(await annotations.read())
    r = {}
    if rules:
        r = json.loads(await rules.read())
    storage.save_dataset(pid, data, r)
    return {"items": len(data.get("items", [])), "annotations": len(data.get("annotations", []))}


@app.post("/projects/{pid}/annotators", dependencies=[Depends(check_key)])
async def upload_annotators(pid: str, annotators: UploadFile = File(...)):
    check_project(pid)
    raw = await annotators.read()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    storage.save_annotators(pid, rows)
    return {"annotators": len(rows)}


@app.get("/projects/{pid}/annotators", dependencies=[Depends(check_key)])
def annotators(pid: str):
    check_project(pid)
    return storage.get_annotators(pid)


@app.post("/projects/{pid}/analyze", dependencies=[Depends(check_key)])
def analyze(pid: str):
    check_project(pid)
    data, rules = storage.get_dataset(pid)
    if data is None:
        raise HTTPException(400, "upload annotations first")
    rep = qa.analyze(data, rules)
    storage.save_report(pid, rep)
    return rep["summary"]


@app.get("/projects/{pid}/report", dependencies=[Depends(check_key)])
def report(pid: str):
    check_project(pid)
    rep = storage.get_report(pid)
    if rep is None:
        raise HTTPException(404, "no report yet")
    return rep


@app.get("/projects/{pid}/review-queue", dependencies=[Depends(check_key)])
def review_queue(pid: str, limit: int = 20):
    return report(pid)["review_queue"][:limit]
