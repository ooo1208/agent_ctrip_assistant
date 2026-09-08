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


class Tools:
    """工具执行端绑定用户与会话，模型参数不能覆盖身份或审批动作。"""
    def __init__(self, store, user, session_id):
        store.own_session(user, session_id)
        self.store, self.user, self.session_id = store, user, session_id

    def search_flights(self, origin, destination, travel_date):
        valid_date(travel_date)
        return [dict(row) for row in self.store.db.execute(
            "SELECT * FROM flights WHERE origin=? AND destination=? AND travel_date=? ORDER BY price_cents",
            (valid_text(origin, "出发地"), valid_text(destination, "目的地"), travel_date))]

    def search_hotels(self, city):
        return [dict(row) for row in self.store.db.execute("SELECT * FROM hotels WHERE city=? ORDER BY nightly_cents",
                                                          (valid_text(city, "城市"),))]

    def propose(self, kind, payload):
        action_id = identifier()
        created = now()
        self.store.db.execute("INSERT INTO actions VALUES(?,?,?,?,?,?,?,?)", (
            action_id, self.session_id, self.user, kind, dump(payload), "pending",
            created.isoformat(), (created + dt.timedelta(minutes=15)).isoformat()))
        return {"action_id": action_id, "status": "pending", "payload": payload,
                "notice": f"尚未下单。核对详情后在终端输入：审批 {action_id}；或：拒绝 {action_id}"}

    def propose_book_flight(self, flight_id, passenger):
        row = self.store.db.execute("SELECT * FROM flights WHERE id=?", (valid_text(flight_id, "flight_id"),)).fetchone()
        if not row or row["seats"] <= 0:
            raise ValueError("航班不存在或已售罄")
        if valid_date(row["travel_date"]) < dt.date.today():
            raise ValueError("航班日期已过期")
        return self.propose("flight", {"flight_id": row["id"], "passenger": valid_text(passenger, "乘机人"),
            "origin": row["origin"], "destination": row["destination"], "travel_date": row["travel_date"],
            "total_cents": row["price_cents"]})

    def propose_book_hotel(self, hotel_id, checkin, checkout, guest):
        first, last = valid_date(checkin), valid_date(checkout)
        if first < dt.date.today() or not 1 <= (last - first).days <= 14:
            raise ValueError("入住须为今天及以后，连续入住 1–14 晚")
        row = self.store.db.execute("SELECT * FROM hotels WHERE id=?", (valid_text(hotel_id, "hotel_id"),)).fetchone()
        if not row:
            raise ValueError("酒店不存在")
        if not self.hotel_available(row, first, last):
            raise ValueError("所选日期存在满房，请更换日期或酒店")
        return self.propose("hotel", {"hotel_id": row["id"], "name": row["name"],
            "guest": valid_text(guest, "入住人"), "checkin": first.isoformat(), "checkout": last.isoformat(),
            "nightly_cents": row["nightly_cents"], "total_cents": row["nightly_cents"] * (last-first).days})

    def hotel_available(self, hotel, first, last):
        day = first
        while day < last:
            occupied = self.store.db.execute(
                "SELECT COUNT(*) FROM orders WHERE kind='hotel' AND resource_id=? AND checkin<=? AND checkout>?",
                (hotel["id"], day.isoformat(), day.isoformat())).fetchone()[0]
            if occupied >= hotel["rooms"]:
                return False
            day += dt.timedelta(days=1)
        return True

    def list_orders(self):
        return [{**dict(row), "details": json.loads(row["details"])} for row in self.store.db.execute(
            "SELECT * FROM orders WHERE user_id=? ORDER BY rowid", (self.user,))]

    def list_pending_actions(self):
        return self.store.pending(self.user, self.session_id)

    def decide(self, action_id, approve):
        """只能由终端显式审批入口调用；在同一写事务中校验、扣减、下单。"""
        with self.store.transaction():
            row = self.store.db.execute(
                "SELECT * FROM actions WHERE id=? AND user_id=? AND session_id=?",
                (action_id, self.user, self.session_id)).fetchone()
            if not row:
                raise ValueError("动作不存在或不属于当前用户/会话")
            if row["status"] == "approved" and approve:
                order = self.store.db.execute("SELECT id FROM orders WHERE action_id=?", (action_id,)).fetchone()
                return {"status": "approved", "order_id": order[0], "reused": True}
            if row["status"] != "pending":
                raise ValueError(f"动作已处于 {row['status']} 状态，不能再次处理")
            if not approve:
                self.store.db.execute("UPDATE actions SET status='rejected' WHERE id=?", (action_id,))
                return {"status": "rejected", "action_id": action_id, "notice": "已拒绝，未创建订单"}
            if now() >= dt.datetime.fromisoformat(row["expires_at"]):
                self.store.db.execute("UPDATE actions SET status='expired' WHERE id=?", (action_id,))
                return {"status": "expired", "notice": "审批已过期，请重新查询并创建待审批动作"}
            payload = json.loads(row["payload"])
            reason = self.recheck(row["kind"], payload)
            if reason:
                self.store.db.execute("UPDATE actions SET status='stale' WHERE id=?", (action_id,))
                return {"status": "stale", "notice": reason + "；未下单，请重新查询并确认"}
            order_id = identifier()
            resource_id = payload["flight_id"] if row["kind"] == "flight" else payload["hotel_id"]
            if row["kind"] == "flight":
                self.store.db.execute("UPDATE flights SET seats=seats-1 WHERE id=?", (resource_id,))
            self.store.db.execute("INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?,?)", (
                order_id, action_id, self.session_id, self.user, row["kind"], resource_id,
                payload.get("checkin"), payload.get("checkout"), payload["total_cents"], dump(payload)))
            self.store.db.execute("UPDATE actions SET status='approved' WHERE id=?", (action_id,))
            return {"status": "approved", "order_id": order_id, "details": payload, "notice": "模拟订单已创建"}

    def recheck(self, kind, payload):
        if kind == "flight":
            row = self.store.db.execute("SELECT * FROM flights WHERE id=?", (payload["flight_id"],)).fetchone()
            if not row or row["seats"] < 1:
                return "航班已售罄或被移除"
            if any(row[key] != payload[key] for key in ("origin", "destination", "travel_date")):
                return "航班行程已变化"
            if row["price_cents"] != payload["total_cents"]:
                return "机票价格已变化"
            if valid_date(row["travel_date"]) < dt.date.today():
                return "航班日期已过期"
        else:
            row = self.store.db.execute("SELECT * FROM hotels WHERE id=?", (payload["hotel_id"],)).fetchone()
            if not row or row["name"] != payload["name"] or row["nightly_cents"] != payload["nightly_cents"]:
                return "酒店或房价已变化"
            first, last = valid_date(payload["checkin"]), valid_date(payload["checkout"])
            if first < dt.date.today() or not self.hotel_available(row, first, last):
                return "入住日期已过期或房间已售罄"
        return None


TOOL_PARAMETERS = {
    "search_flights": ("按出发地、目的地、日期查询模拟航班", ["origin", "destination", "travel_date"]),
    "search_hotels": ("按城市查询模拟酒店，房量还需在提案及审批时校验", ["city"]),
    "propose_book_flight": ("提交机票待审批动作；不会下单", ["flight_id", "passenger"]),
    "propose_book_hotel": ("提交酒店待审批动作；不会下单", ["hotel_id", "checkin", "checkout", "guest"]),
    "list_orders": ("查看当前用户已创建的模拟订单", []),
    "list_pending_actions": ("查看当前会话待审批动作及完整参数", []),
}


class Router:
    def __init__(self, tools):
        self.tools = tools

    def execute(self, name, arguments):
        if name not in TOOL_PARAMETERS or not isinstance(arguments, dict):
            raise ValueError("未知工具或参数不是对象")
        expected = TOOL_PARAMETERS[name][1]
        if set(arguments) != set(expected) or any(not isinstance(value, str) for value in arguments.values()):
            raise ValueError(f"工具 {name} 必须且只能提供文本字段：{expected}")
        workflow = "flight" if "flight" in name else "hotel" if "hotel" in name else "primary"
        self.tools.store.db.execute("UPDATE sessions SET workflow=? WHERE id=? AND user_id=?",
                                   (workflow, self.tools.session_id, self.tools.user))
        result = getattr(self.tools, name)(**arguments)
        return {"route": f"primary → {workflow}", "tool": name, "result": result}


HELP = """离线命令（固定语法，不会调用模型）：
  查航班 上海 北京 YYYY-MM-DD
  订机票 MU5101 张三
  查酒店 北京
  订酒店 BJ01 YYYY-MM-DD YYYY-MM-DD 张三
  待审批 / 订单
  审批 <完整 action_id> / 拒绝 <完整 action_id>
  帮助 / 退出
模型模式可自由表达查询和预订需求，审批仍必须使用上面的终端命令。
金额字段统一为人民币分；模型只操作本地模拟业务数据。
"""


def offline(router, text):
    parts = shlex.split(text)
    mappings = {"查航班": "search_flights", "订机票": "propose_book_flight", "查酒店": "search_hotels",
                "订酒店": "propose_book_hotel", "订单": "list_orders", "待审批": "list_pending_actions"}
    if not parts or parts[0] not in mappings:
        raise ValueError("未识别命令，请输入 帮助；离线模式使用固定命令，不进行自然语言理解")
    name = mappings[parts[0]]
    fields = TOOL_PARAMETERS[name][1]
    if len(parts[1:]) != len(fields):
        raise ValueError(f"参数不完整，需要：{' '.join(fields)}")
    return router.execute(name, dict(zip(fields, parts[1:])))


def handle(router, text):
    tools = router.tools
    tools.store.append_messages(tools.user, tools.session_id, [{"role": "user", "content": text}])
    try:
        command = text.split(maxsplit=1)[0] if text.strip() else ""
        if command in ("审批", "拒绝"):
            parts = shlex.split(text)
            if len(parts) != 2:
                raise ValueError("请提供一个完整 action_id")
            result = tools.decide(parts[1], approve=parts[0] == "审批")
        else:
            result = offline(router, text)
        output = dump(result)
    except (ValueError, RuntimeError) as exc:
        output = dump({"error": str(exc), "notice": "请通过 订单 / 待审批 查看持久化状态"})
    tools.store.append_messages(tools.user, tools.session_id, [{"role": "assistant", "content": output}])
    return output

