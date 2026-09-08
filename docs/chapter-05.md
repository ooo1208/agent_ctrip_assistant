# 第 5 章：完整命令行与可选模型工具协议

本章标签：`chapter-05`。这是本次整理的教学快照，不是官方课程章序或回填的历史开发记录。

## 目标

将模型工具协议接入已有业务边界，确保网络失败不会被伪装为下单成功。

## 读码顺序

`ModelClient.complete` → `model_turn` → `handle` → `main/demo`。模型可调用的 schema 不含审批方法；限制最多 6 轮、每轮最多 8 次工具调用。

## 运行

在仓库根目录执行（不需要第三方依赖和模型密钥）：

```bash
python examples/chapter-05.py
```

完整离线演示：

```bash
python ctrip_agent.py --demo
```

模型模式配置：`.env.example` 仅说明变量，程序不自动加载 `.env`。先由用户环境设置 `MODEL_BASE_URL`、`MODEL_API_KEY`、`MODEL_NAME`，再运行 `python ctrip_agent.py --mode llm`。真实模型会收到本会话消息和合成工具结果。

## 练习

先读 .env.example。自行提供支持 tools/tool_calls 的兼容服务后，再手动测试缺日期、缺乘客、模型声称已审批和服务不可用的场景，记录原始结果。

## 完成标准

离线 demo 创建一张获批机票订单、拒绝酒店订单，并恢复会话；未配置模型时 llm 模式明确报错。实际服务接入需要另行记录效果，不用模拟协议成绩替代。

[返回学习入口](../README.md)
