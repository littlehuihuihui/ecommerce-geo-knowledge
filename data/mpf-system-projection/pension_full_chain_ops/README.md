# 养老金全链路业务（四角色）· 教学 / 面试模块

> **一句话**：把「受托人 / 雇主 / 参保人（成员）/ 平台（eMPF）」串成一条可讲的业务链，并能把对方的诉求翻译成流程节点、合规义务与建模接口。  
> **性质**：教学与面试向业务说明书，**不是**积金局操作手册，也**不是**新的精算引擎。

## 与 `pension_business_chain` 的分工

并行补齐同一 JD 缺口时曾产生两个目录。约定：

| | 本目录 | [`../pension_business_chain/`](../pension_business_chain/) |
|--|--|--|
| 定位 | 口述讲稿 + 可打印一页 + 百科入口 | **交互主台**（阶段筛选 + 20 条诉求） |
| 打开 | [`16_pension_full_chain_ops.html`](../16_pension_full_chain_ops.html) | `business_chain_dashboard.html` |

**诉求主表**以 `pension_business_chain/ticket_interpretation.csv` 为准；本目录 `S01_*.csv` 为 10 条精简练习。

## 怎么读（建议 20–30 分钟）

| 顺序 | 文件 | 用途 |
|------|------|------|
| 1 | [`00_concepts.md`](00_concepts.md) | 概念、链路阶段、制度锚点与诚实边界 |
| 2 | [`01_role_process_demand.md`](01_role_process_demand.md) | 角色 × 流程 × 业务诉求映射 |
| 3 | [`S01_scenario_request_map.csv`](S01_scenario_request_map.csv) | 10 条典型诉求精简表 |
| 4 | [`02_interview_pack.md`](02_interview_pack.md) | 3 分钟口述 + 追问预案 |
| 5 | [`16_pension_full_chain_ops.html`](../16_pension_full_chain_ops.html) | 浏览器一页 / 可打印 |
| 6 | [`../pension_business_chain/business_chain_dashboard.html`](../pension_business_chain/business_chain_dashboard.html) | 交互筛选台（推荐演示） |

## 与现有建模的关系

| 现有成品 | 本模块怎么接 |
|----------|--------------|
| 对象一～四 / 三层替代率 | 供款·提取·充足率旋钮 |
| `pension.html` 北极星 | 覆盖 / 运营指标对齐阶段 |

**明确不做**：受托人市场份额竞争仿真、eMPF 工单级 SLA 仿真。
