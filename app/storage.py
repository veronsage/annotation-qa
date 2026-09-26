import json
import os
import sqlite3
import uuid

DATA_DIR = os.environ.get("AQA_DATA_DIR", "./data")
DB = os.path.join(DATA_DIR, "aqa.sqlite3")

SCHEMA = """
create table if not exists projects (id text primary key, name text, created_at text default current_timestamp);
create table if not exists datasets (project_id text primary key, dataset text, rules text);
create table if not exists annotators (project_id text, annotator_id text, display_name text, email text, level text);
create table if not exists reports (project_id text primary key, report text, created_at text default current_timestamp);
"""


def db():
    os.makedirs(DATA_DIR, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with db() as con:
        con.executescript(SCHEMA)


def project_dir(pid):
    return os.path.join(DATA_DIR, "projects", pid)


def create_project(name):
    pid = uuid.uuid4().hex[:8]
    with db() as con:
        con.execute("insert into projects (id, name) values (?, ?)", (pid, name))
    os.makedirs(project_dir(pid), exist_ok=True)
    return pid


def get_projects():
    with db() as con:
        return [dict(r) for r in con.execute("select * from projects order by created_at")]


def project_exists(pid):
    with db() as con:
        return con.execute("select 1 from projects where id = ?", (pid,)).fetchone() is not None


def save_dataset(pid, dataset, rules):
    with db() as con:
        con.execute("insert or replace into datasets values (?, ?, ?)", (pid, json.dumps(dataset), json.dumps(rules or {})))


def get_dataset(pid):
    with db() as con:
        row = con.execute("select * from datasets where project_id = ?", (pid,)).fetchone()
    if not row:
        return None, None
    return json.loads(row["dataset"]), json.loads(row["rules"])


def save_annotators(pid, rows):
    with db() as con:
        con.execute("delete from annotators where project_id = ?", (pid,))
        for r in rows:
            con.execute(
                "insert into annotators values (?, ?, ?, ?, ?)",
                (pid, r["annotator_id"], r.get("display_name"), r.get("email"), r.get("level")),
            )


def get_annotators(pid):
    with db() as con:
        return [dict(r) for r in con.execute("select * from annotators where project_id = ?", (pid,))]


def save_report(pid, report):
    with db() as con:
        con.execute("insert or replace into reports (project_id, report) values (?, ?)", (pid, json.dumps(report)))


def get_report(pid):
    with db() as con:
        row = con.execute("select report from reports where project_id = ?", (pid,)).fetchone()
    return json.loads(row["report"]) if row else None
