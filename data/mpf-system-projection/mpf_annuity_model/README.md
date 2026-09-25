# 强积金年金化提取模型（对象三延伸）

回答：**把退休余额转为终身年金后，收入结构与长寿风险如何变化？**

## 运行

```bash
cd data/mpf-system-projection/mpf_annuity_model
python run.py
```

打开 `mpf_annuity_dashboard.html`。

## 权衡

**年金化对冲长寿风险，但降低流动性与遗产弹性。**

## 接口

`load_annuity_pricer(csv_path=...)` 可替换为真实产品费率表。
