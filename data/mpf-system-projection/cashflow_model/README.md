# 强积金制度总账户 · 30 年现金流预测模型

对接 Prompt 1-1 数据集与 Prompt 1-2 模型框架。

## 目录结构

```
cashflow_model/
  data_loader.py   # 加载 CSV / Dict 模拟；DataSource 可替换接口
  scenarios.py     # 悲观/基准/乐观控制参数
  model.py         # 核心递推 A_{t+1}=A_t(1+r)+C-W-E
  run.py           # 主入口
  output/          # 运行后生成
```

数据表位于上级目录：`01_core_parameters.csv` … `05_withdrawal_behavior.csv`。

## 环境

```bash
pip install pandas numpy
```

## 运行

```bash
cd data/mpf-system-projection/cashflow_model
python run.py
```

可选参数：

```bash
python run.py --data-dir .. --start 2026 --end 2056 --seed 42
python run.py --output-dir ./output
```

## 输出文件

| 文件 | 内容 |
|---|---|
| `annual_悲观.csv` / `annual_基准.csv` / `annual_乐观.csv` | 逐年资产、供款、提取、净现金流 |
| `annual_all_scenarios.csv` | 三情景合并明细 |
| `summary_comparison.csv` | 三情景对比摘要 |
| `asset_path_wide.csv` | 年份 × 三情景资产宽表 |
| `inflection_depletion.csv` | 下降拐点、资产耗尽年份 |

## 核心恒等式

```
A_{t+1} = A_t × (1 + r_t) + C_t − W_t − E_t
```

- `C_t`：有关入息上下限 + 自雇 5% + 自愿 κ（见 `model.compute_contributions`）
- `W_t`：达龄提取（表5）+ 提前提取 λ（见 `model.compute_withdrawals`）
- `r_t`：表4 基金加权，含保守配置滑移
- `E_t`：φ × A_t 行政费用

## 替换真实业务数据

实现 `data_loader.DataSource` 抽象类，或构造 `DictDataSource(tables={...})`，传入：

```python
from data_loader import DictDataSource
from model import MPFCashflowModel

model = MPFCashflowModel(source=DictDataSource(tables))
```

无需修改 `model.py` 递推逻辑。

## 可复现性

`scenarios.RANDOM_SEED = 42`；`run.py --seed` 可覆盖。本版为确定性情景，种子预留给后续蒙特卡洛扩展。
