from collections import Counter, defaultdict

# значения по умолчанию, rules.json проекта их перезаписывает
DEFAULTS = {
    "allowed_labels": None,
    "min_box_area": 16,
    "min_annotators_per_item": 2,
    "iou_threshold": 0.5,
    "agreement_threshold": 0.66,
    "annotator_min_agreement": 0.7,
}


def iou(a, b):
    # bbox в формате [x, y, w, h]
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[0] + a[2], b[0] + b[2])
    y2 = min(a[1] + a[3], b[1] + b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    union = a[2] * a[3] + b[2] * b[3] - inter
    if union <= 0:
        return 0.0
    return inter / union


def group_boxes(marks, thr):
    # жадно собираем рамки разных разметчиков в группы "один и тот же объект"
    groups = []
    for ann_id, objs in marks.items():
        for o in objs:
            best = None
            best_iou = 0
            for g in groups:
                if ann_id in g["by"]:
                    continue
                v = iou(o["bbox"], g["box"])
                if v > best_iou:
                    best, best_iou = g, v
            if best and best_iou >= thr:
                best["by"][ann_id] = o
            else:
                groups.append({"box": o["bbox"], "by": {ann_id: o}})
    return groups


def check_rules(ann_id, o, item, cfg, allowed):
    res = []
    x, y, w, h = o["bbox"]
    if allowed and o["label"] not in allowed:
        res.append({"type": "unknown_label", "annotator": ann_id, "label": o["label"]})
    if w * h < cfg["min_box_area"]:
        res.append({"type": "box_too_small", "annotator": ann_id})
    if x < 0 or y < 0 or x + w > item["width"] or y + h > item["height"]:
        res.append({"type": "box_out_of_bounds", "annotator": ann_id})
    return res


def analyze(dataset, rules=None):
    cfg = {**DEFAULTS, **(rules or {})}
    allowed = set(cfg["allowed_labels"] or [])

    items = {}
    for it in dataset.get("items", []):
        items[it["item_id"]] = it

    marks = defaultdict(dict)  # item_id -> {annotator_id: objects}
    broken = defaultdict(list)  # записи, которые не смогли разобрать
    unknown = set()
    for a in dataset.get("annotations", []):
        if a.get("item_id") not in items:
            unknown.add(a.get("item_id"))
            continue
        if not isinstance(a.get("objects"), list) or "annotator_id" not in a:
            # не выкидываем молча: объект должен уйти на проверку
            broken[a["item_id"]].append(a.get("annotator_id"))
            continue
        marks[a["item_id"]][a["annotator_id"]] = a["objects"]

    good = Counter()
    total = Counter()
    out = []

    for item_id, item in items.items():
        issues = []
        m = marks.get(item_id, {})
        for ann_id in broken.get(item_id, []):
            issues.append({"type": "bad_annotation", "annotator": ann_id})
        if len(m) < cfg["min_annotators_per_item"]:
            issues.append({"type": "not_enough_annotators", "detail": len(m)})

        for ann_id, objs in m.items():
            for o in objs:
                issues += check_rules(ann_id, o, item, cfg, allowed)

        n = len(m) or 1
        for g in group_boxes(m, cfg["iou_threshold"]):
            if len(g["by"]) < n:
                issues.append({"type": "object_missed", "found_by": sorted(g["by"]), "bbox": g["box"]})
            labels = Counter(o["label"] for o in g["by"].values())
            top, cnt = labels.most_common(1)[0]
            if cnt / len(g["by"]) < cfg["agreement_threshold"]:
                issues.append({"type": "label_conflict", "labels": dict(labels)})
            for ann_id, o in g["by"].items():
                total[ann_id] += 1
                if o["label"] == top and len(g["by"]) == n:
                    good[ann_id] += 1

        # TODO: нормальный скоринг, пока просто 0.25 за каждую проблему
        out.append({"item_id": item_id, "risk_score": round(min(1.0, 0.25 * len(issues)), 2), "issues": issues})

    agreement = {a: round(good[a] / total[a], 3) for a in total}
    queue = [r for r in out if r["issues"]]
    queue.sort(key=lambda r: r["risk_score"], reverse=True)

    return {
        "summary": {
            "items_total": len(items),
            "items_flagged": len(queue),
            "unknown_items": sorted(str(x) for x in unknown),
            "annotators_low_agreement": sorted(a for a in agreement if agreement[a] < cfg["annotator_min_agreement"]),
        },
        "annotator_agreement": agreement,
        "review_queue": queue,
    }
