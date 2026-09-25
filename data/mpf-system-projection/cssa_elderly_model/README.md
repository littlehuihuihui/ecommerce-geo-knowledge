# 综援计划（长者部分）财政支出预测

与强积金模型共用人口层（队列成分法），预测 **2026–2056** 年综援长者年度财政支出。

## 快速运行

```bash
cd data/mpf-system-projection/cssa_elderly_model
python run.py
```

## 核心公式（财政支出，非个人账户）

```
年度支出 = 65+人口 × 综合有效领取率 × 平均月津贴 × 12
综合有效领取率 = 申请率 × 资产审查通过率
```

## 目录

| 文件 | 作用 |
|------|------|
| `population_bridge.py` | 复用 `mpf_model` 人口投影 |
| `eligibility.py` | 合资格层 / 领取率校准 |
| `expenditure.py` | 支出层 |
| `scenarios.py` | 锚点与三情景 |
| `run.py` | 主入口 |
| `00_data_dictionary.md` | 数据字典（运行后生成） |
| `output/` | 逐年 CSV |

详情见运行后生成的 `00_data_dictionary.md`。
