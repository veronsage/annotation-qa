# Прогон baseline на синтетических данных, результаты -> evidence/baseline-probe.txt
# Запуск из корня репозитория:
#   AQA_DATA_DIR=$(mktemp -d) PYTHONPATH=. .venv/bin/python evidence/baseline_probe.py > evidence/baseline-probe.txt
import copy
import json
import os

os.environ.setdefault("AQA_API_KEY", "probe-key")

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app, raise_server_exceptions=False, headers={"X-API-Key": os.environ["AQA_API_KEY"]})
anon = TestClient(app)
base = json.load(open("samples/dataset.json"))
rules = json.load(open("samples/rules.json"))


def upload(pid, ds, r=None):
    files = {"annotations": ("d.json", json.dumps(ds))}
    if r is not None:
        files["rules"] = ("r.json", json.dumps(r))
    return c.post(f"/projects/{pid}/annotations", files=files)


pid = c.post("/projects", json={"name": "probe"}).json()["id"]
upload(pid, base, rules)
with open("samples/annotators.csv", "rb") as f:
    c.post(f"/projects/{pid}/annotators", files={"annotators": f})

# O1 обычный прогон
print("O1", c.post(f"/projects/{pid}/analyze").json())
rep = c.get(f"/projects/{pid}/report").json()
print("   agreement:", rep["annotator_agreement"])
for r in rep["review_queue"]:
    print("  ", r["item_id"], r["risk_score"], [i["type"] for i in r["issues"]])

# O2 без ключа
print("O2 GET /annotators без ключа:", anon.get(f"/projects/{pid}/annotators").status_code)
# O3 ключ один на всех: второй проект видит первый, email отдаётся целиком
other = c.post("/projects", json={"name": "other team"}).json()["id"]
r = c.get(f"/projects/{pid}/annotators")
print("O3 с тем же ключом: проектов видно", len(c.get("/projects").json()), "| поля разметчика:", sorted(r.json()[0]))

# O4 битая запись разметки
ds = copy.deepcopy(base)
ds["annotations"][0] = {"item_id": "img_001", "annotator_id": "a1", "obj": []}
upload(pid, ds, rules)
c.post(f"/projects/{pid}/analyze")
q = c.get(f"/projects/{pid}/report").json()["review_queue"]
print("O4 img_001:", [[i["type"] for i in x["issues"]] for x in q if x["item_id"] == "img_001"])

# O5 разметка на несуществующий item
ds = copy.deepcopy(base)
ds["annotations"].append({"item_id": "img_999", "annotator_id": "a1", "objects": [{"label": "car", "bbox": [1, 1, 50, 50]}]})
upload(pid, ds, rules)
print("O5", c.post(f"/projects/{pid}/analyze").json())

# O6 bbox из двух чисел (на уровне объекта проверки нет)
ds = copy.deepcopy(base)
ds["annotations"][0]["objects"][0]["bbox"] = [1, 2]
upload(pid, ds, rules)
print("O6 analyze status:", c.post(f"/projects/{pid}/analyze").status_code)

# O7 невалидный json
print("O7 upload status:", c.post(f"/projects/{pid}/annotations", files={"annotations": ("d.json", b"{not json")}).status_code)

# O8 правила с нулевыми порогами
upload(pid, base, {"agreement_threshold": 0, "min_annotators_per_item": 0, "iou_threshold": 0})
print("O8", c.post(f"/projects/{pid}/analyze").json())

# O9 большой файл
print("O9 5MB upload:", c.post(f"/projects/{pid}/items", files={"files": ("big.jpg", b"0" * 5_000_000)}).status_code)
