# -*- coding: utf-8 -*-
"""数据加载层：读取 P1（p0_foundation）CSV，并预留真实业务数据接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Union

import pandas as pd

_PKG = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = _PKG.parent / "p0_foundation"

TABLE_FILES = {
    "mortality": "T01_mortality_by_age_sex.csv",
    "population": "T02_population_by_age_sex.csv",
    "contribution": "T03_contribution_parameters.csv",
    "returns": "T04_investment_return.csv",
    "withdrawal": "T05_withdrawal_by_reason.csv",
}


class DataSource(ABC):
    """可替换数据源抽象接口。

    后续接入真实 MPFA / 内部数仓时实现本接口即可，无需改四层计算逻辑。
    """

    @abstractmethod
    def load_mortality(self) -> pd.DataFrame:
        """加载表1：分年龄性别死亡率。"""

    @abstractmethod
    def load_population(self) -> pd.DataFrame:
        """加载表2：分年龄组人口（含基准年）。"""

    @abstractmethod
    def load_contribution_params(self) -> pd.DataFrame:
        """加载表3：缴费与制度参数。"""

    @abstractmethod
    def load_returns(self) -> pd.DataFrame:
        """加载表4：投资回报假设。"""

    @abstractmethod
    def load_withdrawal(self) -> pd.DataFrame:
        """加载表5：提取行为假设。"""


class CSVDataSource(DataSource):
    """从 P1 本地 CSV 加载。"""

    def __init__(self, data_dir: Optional[Union[str, Path]] = None) -> None:
        """初始化。

        Args:
            data_dir: 含 T01–T05 的目录；默认 ``../p0_foundation``。
        """
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        if not self.data_dir.exists():
            raise FileNotFoundError(f"数据目录不存在: {self.data_dir}")

    def _read(self, key: str) -> pd.DataFrame:
        """按键读 CSV。"""
        path = self.data_dir / TABLE_FILES[key]
        if not path.exists():
            raise FileNotFoundError(f"缺少数据表: {path}")
        return pd.read_csv(path)

    def load_mortality(self) -> pd.DataFrame:
        """加载死亡率表。"""
        return self._read("mortality")

    def load_population(self) -> pd.DataFrame:
        """加载人口表。"""
        return self._read("population")

    def load_contribution_params(self) -> pd.DataFrame:
        """加载缴费参数表。"""
        return self._read("contribution")

    def load_returns(self) -> pd.DataFrame:
        """加载回报表。"""
        return self._read("returns")

    def load_withdrawal(self) -> pd.DataFrame:
        """加载提取表。"""
        return self._read("withdrawal")


def load_real_data(config: Optional[dict] = None) -> DataSource:
    """预留：后续替换为真实业务数据源。

    Args:
        config: 连接配置（库地址、API token 等）。当前忽略，返回 CSV 源。

    Returns:
        DataSource 实例。当前实现等价于 ``CSVDataSource()``。

    Note:
        入职后可在此函数内改为 ``WarehouseDataSource(config)``，
        四层模块通过 DataSource 接口读取，无需改公式代码。
    """
    _ = config  # 预留
    return CSVDataSource()


def load_all_tables(
    source: Optional[DataSource] = None,
    data_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, pd.DataFrame]:
    """一次性加载全部 P1 表。

    Args:
        source: 自定义数据源；优先于 data_dir。
        data_dir: CSV 目录。

    Returns:
        键为 mortality / population / contribution / returns / withdrawal。
    """
    src = source or CSVDataSource(data_dir)
    return {
        "mortality": src.load_mortality(),
        "population": src.load_population(),
        "contribution": src.load_contribution_params(),
        "returns": src.load_returns(),
        "withdrawal": src.load_withdrawal(),
    }


# ---------- 制度锚点（可被表3覆盖） ----------
AUM_2026 = 16700.0  # 亿港元 [真实数据] 截至约 2026 年中
AUM_2025YE = 15500.0  # [真实数据] 2025 年底
ACCOUNTS_WAN = 1120.0  # 万个 [真实数据量级]
Y_MIN_DEFAULT = 7100.0  # 现行；2028 起情景切至拟议新值见 scenarios.relevant_income_limits
Y_MAX_DEFAULT = 30000.0
Y_MIN_OLD = 7100.0
Y_MAX_OLD = 30000.0
Y_MIN_NEW = 10500.0  # [假设] 检讨拟议
Y_MAX_NEW = 40000.0
KAPPA_VOL = 0.26  # 自愿占总供款 [真实数据]
COVERAGE = 0.85  # [假设]
EMP_RATE = 0.97  # [假设]
TARGET_CONTRIB_2026 = 912.3  # 校准锚点 [真实数据] 2025-26 财年
