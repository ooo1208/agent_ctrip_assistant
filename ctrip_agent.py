"""原创离线客服 Agent 教学实现；仅使用 Python 3.11 标准库。"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
from pathlib import Path
import shlex
import sqlite3
import sys
import tempfile
import urllib.error
import urllib.request
import uuid


def dump(value):
    return json.dumps(value, ensure_ascii=False)


def identifier():
    return uuid.uuid4().hex


def now():
    return dt.datetime.now(dt.timezone.utc)


def valid_text(value, field, limit=80):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} 必须是 1–{limit} 字符的文本")
    return value.strip()


def valid_date(value):
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("日期必须采用 YYYY-MM-DD") from None


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS sessions(
          id TEXT PRIMARY KEY, user_id TEXT NOT NULL, workflow TEXT NOT NULL DEFAULT 'primary');
        CREATE TABLE IF NOT EXISTS messages(
          id INTEGER PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id), payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS flights(
          id TEXT PRIMARY KEY, origin TEXT NOT NULL, destination TEXT NOT NULL,
          travel_date TEXT NOT NULL, price_cents INTEGER NOT NULL, seats INTEGER NOT NULL CHECK(seats>=0));
        CREATE TABLE IF NOT EXISTS hotels(
          id TEXT PRIMARY KEY, city TEXT NOT NULL, name TEXT NOT NULL,
          nightly_cents INTEGER NOT NULL, rooms INTEGER NOT NULL CHECK(rooms>0));
        CREATE TABLE IF NOT EXISTS actions(
          id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id), user_id TEXT NOT NULL,
          kind TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL,
          created_at TEXT NOT NULL, expires_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS orders(
          id TEXT PRIMARY KEY, action_id TEXT NOT NULL UNIQUE REFERENCES actions(id),
          session_id TEXT NOT NULL, user_id TEXT NOT NULL, kind TEXT NOT NULL, resource_id TEXT NOT NULL,
          checkin TEXT, checkout TEXT, total_cents INTEGER NOT NULL, details TEXT NOT NULL);
        """)
        travel_date = (dt.date.today() + dt.timedelta(days=30)).isoformat()
        with self.transaction():
            self.db.executemany("INSERT OR IGNORE INTO flights VALUES(?,?,?,?,?,?)", [
                ("MU5101", "上海", "北京", travel_date, 68000, 2),
                ("CA1502", "上海", "北京", travel_date, 82000, 3),
                ("CZ3522", "北京", "广州", travel_date, 95000, 2),
            ])
            self.db.executemany("INSERT OR IGNORE INTO hotels VALUES(?,?,?,?,?)", [
                ("BJ01", "北京", "北京教学商务酒店", 42000, 2),
                ("BJ02", "北京", "北京教学经济酒店", 26000, 3),
                ("GZ01", "广州", "广州教学商务酒店", 38000, 2),
            ])

    @contextlib.contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def close(self):
        self.db.close()

    def session(self, user, session_id=None):
        user = valid_text(user, "user", 120)
        if session_id:
            row = self.db.execute("SELECT * FROM sessions WHERE id=? AND user_id=?", (session_id, user)).fetchone()
            if not row:
                raise ValueError("该会话不存在或不属于当前用户")
            return session_id
        session_id = identifier()
        self.db.execute("INSERT INTO sessions(id,user_id) VALUES(?,?)", (session_id, user))
        return session_id

    def own_session(self, user, session_id):
        if not self.db.execute("SELECT 1 FROM sessions WHERE id=? AND user_id=?", (session_id, user)).fetchone():
            raise ValueError("该会话不存在或不属于当前用户")

    def append_messages(self, user, session_id, messages):
        self.own_session(user, session_id)
        with self.transaction():
            self.db.executemany("INSERT INTO messages(session_id,payload) VALUES(?,?)",
                                [(session_id, dump(message)) for message in messages])

    def history(self, user, session_id):
        self.own_session(user, session_id)
        return [json.loads(row[0]) for row in self.db.execute(
            "SELECT payload FROM messages WHERE session_id=? ORDER BY id", (session_id,))]

    def pending(self, user, session_id):
        self.own_session(user, session_id)
        return [self.decode_action(row) for row in self.db.execute(
            "SELECT * FROM actions WHERE user_id=? AND session_id=? AND status='pending' ORDER BY created_at",
            (user, session_id))]

    @staticmethod
    def decode_action(row):
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        return result
