# 强积金制度总账户 · 30年现金流模型

对接 **P0 设计文档** + **P1 数据集**（`../p0_foundation/`）。

## 结构

```
mpf_model/
├── data_loader.py    # 加载 P1；load_real_data() 预留
├── population.py     # 第一层：队列成分法
├── contribution.py   # 第二层：缴费（上下限规则）
├── withdrawal.py     # 第三层：领取（资产反推余额）
├── offsetting.py     # 对冲流出（转制日 2025-05-01 规则）
├── asset.py          # 第四层：A(t+1)=A(t)(1+r)+C−W−Offset
├── scenarios.py      # 3% / 4.9% / 7%
├── run.py            # 主入口
├── run_offsetting.py # 对冲模块自检与 2020–2056 输出
├── validate_analysis.py
└── output/
```

## 运行

```bash
cd data/mpf-system-projection/mpf_model
python run.py
python run_offsetting.py   # 对冲流出 + 有/无对冲资产对比
```

## 校验锚点

- 2026 期初资产 ≈ **16,700** 亿港元
- 2026 总供款 ≈ **912** 亿港元（入息自动校准）
- 默认有关入息上下限：**$10,500 / $40,000**
- 转制日：**2025-05-01**；对冲流出见 `output/offsetting/`

## 替换真实数据

实现 `DataSource` 子类，或在 `load_real_data()` 中返回业务源即可。
