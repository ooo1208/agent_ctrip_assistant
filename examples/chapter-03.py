"""离线合成数据章节示例；从仓库根目录运行。"""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ctrip_agent import Store, Tools

with tempfile.TemporaryDirectory() as directory:
    store = Store(str(Path(directory) / "example.sqlite3"))
    try:
        tools = Tools(store, "lesson-user", store.session("lesson-user"))
        action = tools.propose_book_flight("MU5101", "教学乘客")["action_id"]
        first = tools.decide(action, True)
        second = tools.decide(action, True)
        assert first["order_id"] == second["order_id"] and second["reused"]
        rejected = tools.propose_book_flight("MU5101", "教学乘客二")["action_id"]
        assert tools.decide(rejected, False)["status"] == "rejected"
        assert len(tools.list_orders()) == 1
        print("chapter-03 PASS: 审批幂等，拒绝不下单")
    finally:
        store.close()
