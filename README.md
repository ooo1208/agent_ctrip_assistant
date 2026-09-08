# agent_ctrip_assistant

携程场景旅行客服 Agent 的**原创简化教学版**：学习工具调用、业务流程路由、人工审批、事务复核与持久化会话恢复。

所有航班、酒店、姓名和订单均为合成数据，不连接真实订票系统。本工程使用 Python 3.11+ 标准库；`flight` / `hotel` 是有状态的专业业务流程，不是多个独立大模型。它不是携程真实系统，也不是马士兵课程的官方完整源码。

## 快速开始

克隆后进入本仓库目录，运行：

```bash
python ctrip_agent.py --demo
python -m unittest discover -s . -p "test_*.py" -v
```

无需安装依赖或配置密钥。示例创建临时 SQLite 库并清理；完整 CLI 的普通会话默认存于 `.data/ctrip.sqlite3`。金额统一采用人民币分。

## 当前内容与章节

当前快照包含前 6 章。六个提交是在本次发布中，按依赖与学习顺序整理已有教学实现形成的真实提交；没有回填时间，也不代表六段原始开发周期。章序为本仓库学习安排，不能当作官方课程目录。

| 章 | 内容 | 文档 | Git 标签 |
|---|---|---|---|
| 01 | SQLite 合成数据与持久化会话 | [章节说明](docs/chapter-01.md) | `chapter-01` |
| 02 | 只读工具与待审批预订提案 | [章节说明](docs/chapter-02.md) | `chapter-02` |
| 03 | 审批事务、库存复核与幂等执行 | [章节说明](docs/chapter-03.md) | `chapter-03` |
| 04 | 工具路由、参数边界与会话恢复 | [章节说明](docs/chapter-04.md) | `chapter-04` |
| 05 | 完整命令行与可选模型工具协议 | [章节说明](docs/chapter-05.md) | `chapter-05` |
| 06 | 回归测试、持续集成与完整学习入口 | [章节说明](docs/chapter-06.md) | `chapter-06` |

在工作区干净时执行 `git switch --detach chapter-01` 可查看相应历史代码，执行 `git switch main` 回到完整版本。每章先运行对应的 `examples/chapter-XX.py`；只有最后一章包含完整回归测试和 CI。

## 业务流程

```text
用户输入 → 离线命令 / 可选模型工具调用 → Router → 航班 / 酒店 / 查询流程
                                                   ↓
                                    持久化预订提案（尚未下单）
                                                   ↓
                                  人工输入完整 action_id 审批
                                                   ↓
                             写事务：身份/时效/价格/库存复核 → 模拟订单
```

模型可调用的工具列表没有审批入口。审批绑定用户、会话、完整参数与报价，重复批准返回原订单。酒店按每一晚检查占用，离店日不计入占用。

## 范围与限制

- 默认离线入口采用固定命令语法，不宣称具备自然语言理解效果。
- 完整版提供兼容 Chat Completions 的模型接口；真实模型尚未连通验收，不宣称准确率、延迟或生产效果。
- `--user` 是可信本地操作者指定的身份，不是登录认证；部署 Web 服务时需要接入服务端认证。
- 会话消息完整保存在 SQLite，当前没有摘要、上下文裁剪、外部支付、分布式事务或正式携程 API。
- 测试中的 FakeClient 只验证工具调用协议，不替代真实模型效果评估。

## 来源与许可

- [来源及归属说明](SOURCES.md)：区分官方架构参考、课程主题与本次原创实现。
- [LangGraph 官方旅行客服历史教程](https://github.com/langchain-ai/langgraph/blob/139cad373b6cf712d0b6d456c698559b59073812/docs/docs/tutorials/customer-support/customer-support.ipynb)：架构学习参考，历史 API 与当前框架版本可能不同。
- [马士兵携程 AI 智能助手课程入口](https://www.mashibing.com/course/2801)：课程主题参考，不表示本仓库具有官方身份。

本仓库原创代码与原创文档采用 [MIT License](LICENSE)。外部链接资料及第三方商标归各自权利人所有；本仓库没有重新许可或复制外部课件。

## 完整版使用与验证

[完整使用手册](docs/使用手册.md) 说明交互命令、恢复会话、模型环境变量和业务限制。

```bash
python ctrip_agent.py --user alice
python ctrip_agent.py --user alice --session <此前打印的完整会话编号>
```

配置可选真实模型时，请参考 `.env.example`，程序不会自动读取 `.env`。密钥只放在自己的环境变量中，不进入 Git。

本地 Python 3.11 已通过 13 项测试与完整离线演示。CI 同时配置 Python 3.11/3.12；远端执行结果以 Actions 状态为准。所有验证使用合成数据和临时数据库，模型相关测试采用明确标注的模拟协议对象，不消耗模型 Token。

完整学习路线见 [Agent-Learning](https://github.com/ooo1208/Agent-Learning)，综合采购业务工程见 [ERP_OPENCLAW](https://github.com/ooo1208/ERP_OPENCLAW)。
