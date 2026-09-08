"""离线合成数据章节示例；从仓库根目录运行。"""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
from ctrip_agent import Store, Tools, Router, handle

with tempfile.TemporaryDirectory() as directory:
    path = str(Path(directory) / "example.sqlite3")
    store = Store(path)
    session = store.session("lesson-user")
    router = Router(Tools(store, "lesson-user", session))
    result = json.loads(handle(router, "订机票 MU5101 教学乘客"))
    action = result["result"]["action_id"]
    assert result["route"] == "primary → flight"
    store.close()
    store = Store(path)
    try:
        router = Router(Tools(store, "lesson-user", store.session("lesson-user", session)))
        assert router.tools.list_pending_actions()[0]["id"] == action
        assert len(store.history("lesson-user", session)) == 2
        assert json.loads(handle(router, "审批 " + action))["status"] == "approved"
        print("chapter-04 PASS: 专业流程路由与重启后审批恢复")
    finally:
        store.close()
