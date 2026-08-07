# 多行业数据百科

在线地址（GitHub Pages）：https://littlehuihuihui.github.io/industry-data-encyclopedia/

行业知识框架、指标字典、方法论与 RAG 搜索入口。

## 简历三件套互链

| 作品 | 地址 |
|------|------|
| 个人展馆 | https://littlehuihuihui.github.io/data-analyst-gallery/ |
| 多行业数据平台 | https://littlehuihuihui.github.io/financial-data-portfolio/ |
| 本百科 | https://littlehuihuihui.github.io/industry-data-encyclopedia/ |

## 本地

```bash
python -m http.server 8091
```

三板/导航知识图谱 2.0：`knowledge-graph.html`  
三阶段：搜索引导 → 模块概览 → 单节点辐射探索。  
数据：`knowledge-graph-data.js`（由 `_build_knowledge_graph_data.py` 从三页抽取）。

原按行业分图谱仍保留为 `graph.html`（可选）。


RAG（可选）：见 `rag/README.md`（向量库目录勿提交大文件）。
