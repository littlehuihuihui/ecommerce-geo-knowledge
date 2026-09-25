# 强积金 · 代表性个体账户充足率模型

回答：**从入职到退休，强积金够不够用？账户耗尽年龄分布如何？**

## 运行

```bash
cd data/mpf-system-projection/mpf_individual_model
python run.py
```

打开 `mpf_individual_adequacy_dashboard.html` 查看积累曲线与耗尽年龄直方图。

## 四层

1. 职业生涯模拟（入息、上下限、供款中断）
2. 退休时余额（供款 vs 投资收益、相对前年薪倍数）
3. 提取方式 → 耗尽年龄
4. 长寿风险蒙特卡洛（分性别）

## 制度局限

**强积金不提供长寿风险保障**——无一笔过强制转为终身年金；存活超过账户耗尽年龄后无自动续付。

## 真实个体接口

`data_loader.load_real_individual(person_id, csv_path=...)`
