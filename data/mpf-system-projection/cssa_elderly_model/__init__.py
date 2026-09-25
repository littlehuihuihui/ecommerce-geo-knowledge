# -*- coding: utf-8 -*-
"""综援计划（长者部分）财政支出预测模型。

与强积金模型的关键区别：
  - 综援是**政府财政支出**，不是个人账户累积
  - 核心恒等式：年度支出 = 合资格长者人数 × 平均每月津贴 × 12
  - 人口层与 ``mpf_model.population`` **共用**队列成分法，保证一致性

用法::

    python run.py
"""

from __future__ import annotations

__version__ = "0.1.0"
