"""离线合成数据章节示例；从仓库根目录运行。"""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ctrip_agent import Store, Tools, Router, handle

class FakeClient:
    """仅验证协议形状，不代表任何真实模型效果。"""
    calls = 0

    def complete(self, messages):
        self.calls += 1
        if self.calls == 1:
            return {"role": "assistant", "content": None, "tool_calls": [{
                "id": "example-call", "type": "function", "function": {
                    "name": "propose_book_flight",
                    "arguments": '{"flight_id":"MU5101","passenger":"教学乘客"}'}}]}
        assert messages[-1]["role"] == "tool"
        return {"role": "assistant", "content": "已提出预订申请，请人工审批。"}

with tempfile.TemporaryDirectory() as directory:
    store = Store(str(Path(directory) / "example.sqlite3"))
    try:
        tools = Tools(store, "lesson-user", store.session("lesson-user"))
        assert "人工审批" in handle(Router(tools), "帮教学乘客预订 MU5101", FakeClient())
        assert len(tools.list_pending_actions()) == 1
        assert tools.list_orders() == []
        print("chapter-05 PASS: 模拟工具协议只创建提案，真实模型尚未实测")
    finally:
        store.close()
