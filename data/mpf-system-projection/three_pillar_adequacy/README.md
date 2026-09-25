# 三层退休收入合并 · 可勾选成品（P0+P1）

学习：**长者生活津贴、综援、生果金、强积金、年金** 的差别，并算合并替代率。

## 成品怎么用

打开 `three_pillar_dashboard.html`（或 `output/` 下同名文件）：

1. **模块开关** — 每个模块两列  
   - **展示**：概念卡 / 图例 / 表列是否出现  
   - **计入统计**：是否算进初期·地板替代率与合计  
2. **情景多选** — 只对比你关心的画像  
3. **预设** — 一键「只看长寿地板」「只看强积金+年金」「学长津」等  

公式会随勾选变化；强积金提取**默认不进地板**（花光后没有了）。

## 运行 / 重新生成

```bash
cd data/mpf-system-projection/three_pillar_adequacy
python run.py
```

先读 [`00_concepts.md`](00_concepts.md)，再打开仪表盘。

## 依赖

会读取对象四 `mpf_annuity_model/output/T01_income_by_annuitize_ratio.csv`（请先跑过年金模型）。
