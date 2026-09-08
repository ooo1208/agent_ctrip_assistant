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
        date = store.db.execute("SELECT travel_date FROM flights WHERE id='MU5101'").fetchone()[0]
        before = store.db.execute("SELECT seats FROM flights WHERE id='MU5101'").fetchone()[0]
        assert tools.search_flights("上海", "北京", date)
        action = tools.propose_book_flight("MU5101", "教学乘客")
        assert action["status"] == "pending"
        assert tools.list_orders() == []
        assert store.db.execute("SELECT seats FROM flights WHERE id='MU5101'").fetchone()[0] == before
        print("chapter-02 PASS: 查询和预订提案可用，尚未扣库存或下单")
    finally:
        store.close()
