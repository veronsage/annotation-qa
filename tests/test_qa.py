import json
from pathlib import Path

from app.qa import analyze, iou

SAMPLES = Path(__file__).parent.parent / "samples"


def run():
    ds = json.loads((SAMPLES / "dataset.json").read_text())
    rules = json.loads((SAMPLES / "rules.json").read_text())
    return analyze(ds, rules)


def issues_of(rep, item_id):
    for r in rep["review_queue"]:
        if r["item_id"] == item_id:
            return [i["type"] for i in r["issues"]]
    return []


def test_iou():
    assert iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0
    assert iou([0, 0, 10, 10], [20, 20, 5, 5]) == 0.0


def test_good_item_not_in_queue():
    assert issues_of(run(), "img_001") == []


def test_label_conflict():
    assert "label_conflict" in issues_of(run(), "img_002")


def test_missed_object():
    assert "object_missed" in issues_of(run(), "img_003")


def test_one_annotator():
    assert "not_enough_annotators" in issues_of(run(), "img_005")


def test_broken_record_goes_to_queue():
    ds = json.loads((SAMPLES / "dataset.json").read_text())
    ds["annotations"][0] = {"item_id": "img_001", "annotator_id": "a1"}
    rep = analyze(ds)
    assert "bad_annotation" in issues_of(rep, "img_001")


def test_unknown_item_reported():
    ds = json.loads((SAMPLES / "dataset.json").read_text())
    ds["annotations"].append({"item_id": "img_999", "annotator_id": "a1", "objects": []})
    assert analyze(ds)["summary"]["unknown_items"] == ["img_999"]
