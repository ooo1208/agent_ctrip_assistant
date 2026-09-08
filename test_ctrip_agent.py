"""验证真实持久化边界；不用网络或外部依赖。"""
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ctrip_agent import Store, Tools, Router, ModelClient, handle, now


class BookingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = str(Path(self.directory.name) / "test.sqlite3")
        self.store = Store(self.path)
        self.session = self.store.session("alice")
        self.alice = Tools(self.store, "alice", self.session)
        self.bob = Tools(self.store, "bob", self.store.session("bob"))
        self.date = (dt.date.today() + dt.timedelta(days=30)).isoformat()
        self.checkout = (dt.date.today() + dt.timedelta(days=32)).isoformat()

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def seats(self):
        return self.store.db.execute("SELECT seats FROM flights WHERE id='MU5101'").fetchone()[0]

    def status(self, action):
        return self.store.db.execute("SELECT status FROM actions WHERE id=?", (action,)).fetchone()[0]

    def test_proposal_is_not_order_and_rejection_does_not_consume_inventory(self):
        seats = self.seats()
        action = self.alice.propose_book_flight("MU5101", "张三")["action_id"]
        self.assertEqual([], self.alice.list_orders())
        self.assertEqual(seats, self.seats())
        self.assertEqual("rejected", self.alice.decide(action, False)["status"])
        self.assertEqual([], self.alice.list_orders())
        self.assertEqual(seats, self.seats())
        with self.assertRaises(ValueError):
            self.alice.decide(action, True)

    def test_approval_is_idempotent(self):
        seats = self.seats()
        action = self.alice.propose_book_flight("MU5101", "张三")["action_id"]
        first, second = self.alice.decide(action, True), self.alice.decide(action, True)
        self.assertEqual(first["order_id"], second["order_id"])
        self.assertTrue(second["reused"])
        self.assertEqual(1, len(self.alice.list_orders()))
        self.assertEqual(seats - 1, self.seats())

    def test_user_and_session_isolation(self):
        action = self.alice.propose_book_flight("MU5101", "张三")["action_id"]
        with self.assertRaises(ValueError):
            self.bob.decide(action, True)
        with self.assertRaises(ValueError):
            self.store.session("bob", self.session)
        with self.assertRaises(ValueError):
            self.store.history("bob", self.session)
        another_alice = Tools(self.store, "alice", self.store.session("alice"))
        with self.assertRaises(ValueError):
            another_alice.decide(action, True)
        self.alice.decide(action, True)
        self.assertEqual([], self.bob.list_orders())
        self.assertEqual([], self.bob.list_pending_actions())

    def test_restart_preserves_pending_approval_and_conversation(self):
        response = json.loads(handle(Router(self.alice), "订机票 MU5101 张三"))
        action = response["result"]["action_id"]
        self.store.close()
        self.store = Store(self.path)
        restored = Tools(self.store, "alice", self.store.session("alice", self.session))
        self.assertEqual(action, restored.list_pending_actions()[0]["id"])
        self.assertEqual(2, len(self.store.history("alice", self.session)))
        self.assertEqual("approved", restored.decide(action, True)["status"])

    def test_price_change_invalidates_exact_proposal(self):
        action = self.alice.propose_book_flight("MU5101", "张三")["action_id"]
        self.store.db.execute("UPDATE flights SET price_cents=price_cents+100 WHERE id='MU5101'")
        self.assertEqual("stale", self.alice.decide(action, True)["status"])
        self.assertEqual("stale", self.status(action))
        self.assertEqual([], self.alice.list_orders())

    def test_flight_inventory_rechecked_after_other_users_book(self):
        self.store.db.execute("UPDATE flights SET seats=1 WHERE id='MU5101'")
        first = self.alice.propose_book_flight("MU5101", "张三")["action_id"]
        second = self.bob.propose_book_flight("MU5101", "李四")["action_id"]
        self.assertEqual("approved", self.bob.decide(second, True)["status"])
        self.assertEqual("stale", self.alice.decide(first, True)["status"])
        self.assertEqual(0, self.seats())
        self.assertEqual([], self.alice.list_orders())

    def test_hotel_overlapping_nights_rechecked_and_checkout_is_exclusive(self):
        self.store.db.execute("UPDATE hotels SET rooms=1 WHERE id='BJ01'")
        first = self.alice.propose_book_hotel("BJ01", self.date, self.checkout, "张三")["action_id"]
        second = self.bob.propose_book_hotel("BJ01", self.date, self.checkout, "李四")["action_id"]
        self.assertEqual("approved", self.bob.decide(second, True)["status"])
        self.assertEqual("stale", self.alice.decide(first, True)["status"])
        next_checkout = (dt.date.fromisoformat(self.checkout) + dt.timedelta(days=1)).isoformat()
        next_action = self.alice.propose_book_hotel("BJ01", self.checkout, next_checkout, "张三")["action_id"]
        self.assertEqual("approved", self.alice.decide(next_action, True)["status"])

    def test_expired_action_is_persistently_invalid(self):
        action = self.alice.propose_book_flight("MU5101", "张三")["action_id"]
        self.store.db.execute("UPDATE actions SET expires_at=? WHERE id=?",
                              ((now()-dt.timedelta(seconds=1)).isoformat(), action))
        self.assertEqual("expired", self.alice.decide(action, True)["status"])
        self.assertEqual("expired", self.status(action))
        self.assertEqual([], self.alice.list_orders())

    def test_router_cannot_call_approval_or_override_identity(self):
        router = Router(self.alice)
        with self.assertRaises(ValueError):
            router.execute("decide", {"action_id": "x", "approve": "true"})
        with self.assertRaises(ValueError):
            router.execute("list_orders", {"user": "bob"})
        with self.assertRaises(ValueError):
            router.execute("search_hotels", {"city": 3})

    def test_sql_input_is_data_and_missing_slots_do_not_create_action(self):
        self.assertEqual([], self.alice.search_hotels("北京' OR 1=1 --"))
        response = json.loads(handle(Router(self.alice), "订机票 MU5101"))
        self.assertIn("error", response)
        self.assertEqual([], self.alice.list_pending_actions())

    def test_model_transport_failure_is_reported_and_never_books(self):
        class BrokenClient:
            def complete(self, messages):
                raise RuntimeError("模型连接失败或超时")
        result = json.loads(handle(Router(self.alice), "帮我订一张机票", BrokenClient()))
        self.assertIn("模型连接失败", result["error"])
        self.assertEqual([], self.alice.list_orders())
        self.assertEqual([], self.alice.list_pending_actions())

    def test_model_tool_protocol_creates_only_proposal(self):
        class FakeProtocolClient:
            calls = 0
            def complete(self, messages):
                self.calls += 1
                if self.calls == 1:
                    return {"role": "assistant", "content": None, "tool_calls": [{
                        "id": "call_test", "type": "function", "function": {
                            "name": "propose_book_flight", "arguments": '{"flight_id":"MU5101","passenger":"张三"}'}}]}
                self.assertion = messages[-1]["role"]
                return {"role": "assistant", "content": "已提出申请，需要终端审批。"}
        client = FakeProtocolClient()
        self.assertIn("终端审批", handle(Router(self.alice), "给张三订 MU5101", client))
        self.assertEqual("tool", client.assertion)
        self.assertEqual(1, len(self.alice.list_pending_actions()))
        self.assertEqual([], self.alice.list_orders())

    def test_llm_mode_requires_explicit_configuration(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "MODEL_BASE_URL"):
                ModelClient()


if __name__ == "__main__":
    unittest.main(verbosity=2)
