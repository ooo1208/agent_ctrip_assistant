# 来源、归属与章节形成方式

## 本仓库的实现

本仓库 Python 代码、合成业务数据、测试、章节示例与说明是本次为学习目的编写和整理的原创简化实现，采用 MIT。没有复制未知许可的学员仓库代码、付费课件、用户简历或真实客户数据。名称仅用于标明旅行客服教学场景，不表示与携程或课程机构存在关联。

六章以实际依赖为顺序，将已有教学实现整理为可运行代码快照。所有 Git 提交使用实际整理时间，没有伪造历史开发时间；这些章名不是官方课程目录，也不表示恢复出了官方完整教学代码。

## 架构参考

1. [LangGraph 官方旅行客服教程固定版本](https://github.com/langchain-ai/langgraph/blob/139cad373b6cf712d0b6d456c698559b59073812/docs/docs/tutorials/customer-support/customer-support.ipynb)：参考从单助手到专业流程、敏感工具审批与状态恢复的教学模式。该文档归 LangChain / LangGraph 原作者所有，原项目许可见 [同提交 LICENSE](https://github.com/langchain-ai/langgraph/blob/139cad373b6cf712d0b6d456c698559b59073812/LICENSE)。本仓库仅提供链接，没有将该 notebook 或第三方课件复制进来。
2. [马士兵携程 AI 智能助手课程入口](https://www.mashibing.com/course/2801)：用于确认课程主题与学习方向；不是本仓库代码来源声明，也不能证明本仓库属于官方发布。
3. [公开单助手工程线索](https://github.com/gdemoni/Simple-Single-Agent-Ctrip-Assistant) 与 [公开专业流程工程线索](https://github.com/gdemoni/agent_ctrip_assistant)：用于理解项目命名和学习阶段。未确认官方发布身份；本仓库没有复制其源代码或声称补齐其付费内容。

## 与完整版课程 / 生产系统的差距

本实现使用标准库 SQLite 和轻量 Router，没有引入 LangGraph 框架，没有真实携程接口、Web 登录、外部支付、租车/景点流程、生产数据库或分布式执行器。`flight` / `hotel` 是专业业务流程，不代表运行了多个独立模型实例。真实模型接口已经编写但未使用商业密钥实测；模拟协议测试不构成真实模型质量评估。

MIT 只适用于本仓库原创内容，不覆盖外部链接材料、第三方商标及其名称。
