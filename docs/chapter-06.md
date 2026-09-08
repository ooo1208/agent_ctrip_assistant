# 第 6 章：回归测试、持续集成与完整学习入口

本章标签：`chapter-06`。这是本次整理的教学快照，不是官方课程章序或回填的历史开发记录。

## 目标

用能阻止业务回归的测试验证最终工程，并通过 CI 重复执行离线场景。

## 读码顺序

`test_ctrip_agent.py` → `.github/workflows/ci.yml` → `docs/使用手册.md`。13 项测试覆盖审批幂等、隔离、持久化、报价/库存/时效变化、参数边界和模型协议失败。

## 运行

在仓库根目录执行（不需要第三方依赖和模型密钥）：

```bash
python examples/chapter-06.py
```

完整验证：

```bash
python -m unittest discover -s . -p "test_*.py" -v
python ctrip_agent.py --demo
```

## 练习

尝试破坏 decide 的价格复核，观察对应测试失败，再恢复代码。随后增加一个自己实现的业务能力及其失败案例，不编造真实业务效果。

## 完成标准

13 项 unittest 通过，完整 demo 通过。CI 配置在 Python 3.11/3.12 执行相同流程；远端结果以 GitHub Actions 实际运行状态为准。

[返回学习入口](../README.md)
