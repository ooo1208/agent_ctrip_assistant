"""离线合成数据章节示例；从仓库根目录运行。"""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ctrip_agent import Store

with tempfile.TemporaryDirectory() as directory:
    path = str(Path(directory) / "example.sqlite3")
    store = Store(path)
    session = store.session("lesson-user")
    store.append_messages("lesson-user", session, [{"role": "user", "content": "查询合成航班"}])
    store.close()
    store = Store(path)
    try:
        assert store.session("lesson-user", session) == session
        assert store.history("lesson-user", session)[0]["content"] == "查询合成航班"
        print("chapter-01 PASS: 会话和消息在关闭数据库后仍然存在")
    finally:
        store.close()
