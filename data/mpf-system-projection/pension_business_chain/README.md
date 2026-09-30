# 养老金全链路业务 · JD 对齐补充模块

> 岗位要求：熟悉养老金全链路（**受托人 / 雇主 / 参保人 / 平台**），精准解读业务诉求。

## 与 `pension_full_chain_ops` 的分工（勿当两套互斥主库）

| 目录 | 用途 |
|------|------|
| **本目录 `pension_business_chain`** | **交互主台**：7 阶段矩阵 + **20** 条诉求解读 + 可筛选 HTML |
| `pension_full_chain_ops` + `16_*.html` | **口述/可打印**：3 分钟讲稿、精简映射、百科导航入口 |

诉求主表以本目录 `ticket_interpretation.csv` 为准；`S01_scenario_request_map.csv` 为精简练习集。

## 覆盖结论

**现成对象一～四 + 三层替代率：未充分覆盖本条。**  
详见 [`00_coverage_vs_jd.md`](00_coverage_vs_jd.md)。

## 怎么读

1. `00_coverage_vs_jd.md` — 对照表与结论  
2. `01_full_chain_concepts.md` — 链路与角色说明  
3. `business_chain_dashboard.html` — 按角色筛选  
4. `02_interview_pack.md` — 3 分钟口述 + 追问  
5. 源表：`role_stage_matrix.csv` · `ticket_interpretation.csv`

```bash
cd data/mpf-system-projection/pension_business_chain
python build_dashboard.py
```

## 和对象一～四

宏观看池子与替代率；本模块看**谁在推水流、原话怎么拆**。eMPF 在对象一是费率，在本模块是平台角色。
