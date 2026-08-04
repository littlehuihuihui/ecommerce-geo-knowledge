# 行业百科 RAG 智能搜索系统

## 简介

基于语义理解的行业知识检索系统，支持用自然语言搜索整个百科的内容。

## 功能特性

- 🔍 **语义搜索**：基于向量相似度的语义检索，不只是关键词匹配
- 💡 **智能问答**：从知识库中提取相关内容回答问题
- 📚 **12大行业覆盖**：新能源、文旅、物流、电商、零售、制造、SaaS、游戏、金融、在线教育、直播电商、本地生活
- 🎯 **精准定位**：直接跳转到相关内容页面

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 构建索引

首次使用需要构建向量索引：

```bash
python build_index.py
```

这会：
- 扫描所有 HTML 页面
- 提取文本内容并分块
- 下载 embedding 模型（首次运行自动下载）
- 向量化并存入 ChromaDB

### 3. 启动服务

```bash
python app.py
```

启动后访问：http://localhost:5000

## 文件结构

```
rag/
├── app.py              # Flask 后端服务
├── build_index.py      # 索引构建脚本
├── requirements.txt    # 依赖列表
├── search.html         # 搜索页面
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
