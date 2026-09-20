# 行业百科 RAG 智能搜索系统

## 简介

基于语义理解的行业知识检索系统，支持用自然语言搜索整个百科的内容。

## 功能特性

- 🔍 **语义搜索**：基于向量相似度的语义检索，不只是关键词匹配
- 💡 **智能问答**：从知识库中提取相关内容回答问题
- 📚 **全站页面覆盖**：自动发现根目录与子目录下的所有知识页面（含金融 6 个方向：总览 / 银行 / 保险 / 证券资管 / 支付 / 养老金）
- 🎯 **精准定位**：直接跳转到相关内容页面

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 构建索引

首次使用（或更新了百科内容后）需要构建向量索引：

```bash
python build_index.py
```

这会：
- **自动扫描**根目录与子目录下所有合格的 HTML 页面（无需手工维护清单）
- 提取文本内容并分块（500 字 / 100 字重叠）
- 加载 embedding 模型 `BAAI/bge-small-zh-v1.5`（首次运行自动下载，约 100MB）
- 向量化并存入 ChromaDB

构建完成后会自动做一次自检检索，输出索引向量数。(当前基线：24 个页面 → 268 个向量)

### 3. 启动服务

```bash
python app.py
```

启动后访问：http://localhost:5000

## 新增/更新页面后如何重建

1. 直接执行 `python build_index.py` 即可——页面清单是自动发现的，新增 `xxx.html` 无需改脚本。
2. 如需排除某页，编辑 `build_index.py` 顶部的 `EXCLUDE_FILES`（下划线开头的临时文件与小于 1KB 的跳转桩页已自动跳过）。
3. 重建会**先删除同名 collection**，旧索引数据目录无需手工清理。

## 环境兼容说明（Windows / 旧 Python）

本仓库的 RAG 依赖对运行环境有两条硬性要求，`build_index.py` 已内置自动兼容处理：

| 问题 | 触发条件 | 自动处理 |
| --- | --- | --- |
| `chromadb requires sqlite3 >= 3.35` | Python 3.8 自带 sqlite3 3.32 | `_ensure_sqlite_supported()` 会从本机其他 Python 安装（Python39/31x）或环境变量 `SQLITE3_DLL` 指定的路径，在导入 chromadb **之前**预加载新版 `sqlite3.dll`（非侵入，不修改 Python 安装） |
| `import posthog` 失败（`dict[str, ...]` 需要 3.9+） | Python 3.8 环境 | `_ensure_posthog_importable()` 注入 `rag/_stubs/posthog.py` 空实现桩模块，不上报任何遥测数据 |
| 旧版打包依赖覆盖 site-packages | `rag/packages`、`D:\rag_pkgs` 内含旧 `typing_extensions` | `_ensure_deps_on_path()` 优先使用环境已安装的依赖，仅在导入失败时才注入打包路径 |

> 建议：条件允许时使用 **Python 3.11** 运行本模块，可完全避免上述兼容处理。

## 文件结构

```
rag/
├── app.py              # Flask 后端服务
├── build_index.py      # 索引构建脚本（自动发现页面 + 环境兼容垫片）
├── requirements.txt    # 依赖列表
├── search.html         # 搜索页面
├── _stubs/posthog.py   # posthog 空实现桩模块（仅旧 Python 需要）
└── data/
    └── chroma/         # 向量数据库（自动生成）
```

## API 接口

### 语义搜索

```
POST /api/search
Content-Type: application/json

{
  "query": "SaaS的核心指标",
  "n_results": 5
}
```

### 智能问答

```
POST /api/ask
Content-Type: application/json

{
  "question": "什么是LTV/CAC？",
  "n_results": 3
}
```

### 统计信息

```
GET /api/stats
```

## 技术栈

- **后端**：Flask
- **向量数据库**：ChromaDB
- **Embedding 模型**：BAAI/bge-small-zh-v1.5
- **前端**：原生 HTML/CSS/JS

## 注意事项

1. 首次运行需要下载 embedding 模型（约 100MB），请耐心等待
2. 索引构建完成后，后续启动直接加载，速度很快
3. 如果更新了百科内容，需要重新运行 `build_index.py` 更新索引
4. 目前的问答是抽取式的（从检索结果中提取），如需生成式问答需要接入 LLM
5. 若索引目录由**不同版本的 chromadb** 生成，升级后读取旧 collection 可能报 `KeyError: '_type'`；
   此时把 `data/chroma` 改名备份后重建即可（旧数据无法迁移）
