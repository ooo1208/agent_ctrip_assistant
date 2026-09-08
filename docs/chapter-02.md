# 第 2 章：只读工具与待审批预订提案

本章标签：`chapter-02`。这是本次整理的教学快照，不是官方课程章序或回填的历史开发记录。

## 目标

用只读查询和“预订提案”表达模型工具边界，理解提案不会直接扣库存。

## 读码顺序

`Tools.search_flights/search_hotels` → `propose_book_flight/propose_book_hotel` → `propose` → `hotel_available`。提案包含动作编号、乘客、行程、价格和时效。

## 运行

在仓库根目录执行（不需要第三方依赖和模型密钥）：

```bash
python examples/chapter-02.py
```

## 练习

为航班查询增加最高价格参数。分别尝试正常城市与 SQL 片段形式的城市，确认输入只是查询数据。

## 完成标准

查询返回合成航班，提案状态为 pending，订单数量仍为 0，座位数没有减少。

[返回学习入口](../README.md)
