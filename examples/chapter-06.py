"""离线合成数据章节示例；从仓库根目录运行。"""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import subprocess

root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py", "-v"],
               cwd=root, check=True)
subprocess.run([sys.executable, "ctrip_agent.py", "--demo"], cwd=root, check=True)
print("chapter-06 PASS: 完整离线测试与演示通过")
