# -*- coding: utf-8 -*-
"""数据加载层：读取 Prompt 1-1 CSV，并预留真实业务数据替换接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union

import numpy as np
import pandas as pd

from scenarios import RANDOM_SEED


_PKG_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = _PKG_DIR.parent

TABLE_FILES: Dict[str, str] = {
    "core": "01_core_parameters.csv",
    "population": "02_population_projection.csv",
    "contrib": "03_contributing_population.csv",
    "returns": "04_investment_return_assumptions.csv",
    "withdrawal": "05_withdrawal_behavior.csv",
}


class DataSource(ABC):
    """可替换数据源抽象接口。

    后续接入真实 MPFA / 内部数仓时，实现本接口即可，无需改 model.py。
    """

    @abstractmethod
    def load_core_parameters(self) -> pd.DataFrame:
        """加载表1：核心参数（含初值 AUM）。"""

    @abstractmethod
    def load_contributing_population(self) -> pd.DataFrame:
        """加载表3：缴费人口与供款路径。"""

    @abstractmethod
    def load_investment_returns(self) -> pd.DataFrame:
        """加载表4：分基金类型回报与配置权重。"""

    @abstractmethod
    def load_withdrawal_behavior(self) -> pd.DataFrame:
        """加载表5：达龄提取行为。"""

    def load_population(self) -> Optional[pd.DataFrame]:
        """可选：表2 人口投影（本版核心递推可不依赖）。"""
        return None


class CSVDataSource(DataSource):
    """从 Prompt 1-1 产出的本地 CSV 加载数据。"""

    def __init__(self, data_dir: Optional[Union[str, Path]] = None) -> None:
        """初始化 CSV 数据源。

        Args:
            data_dir: 含 01–05 CSV 的目录；默认本包上级目录。
        """
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        if not self.data_dir.exists():
            raise FileNotFoundError(f"数据目录不存在: {self.data_dir}")

    def _read(self, key: str) -> pd.DataFrame:
        """按表键读取 CSV。"""
        path = self.data_dir / TABLE_FILES[key]
        if not path.exists():
            raise FileNotFoundError(f"缺少数据表: {path}")
        return pd.read_csv(path)

    def load_core_parameters(self) -> pd.DataFrame:
        """加载表1。"""
        return self._read("core")

    def load_contributing_population(self) -> pd.DataFrame:
        """加载表3。"""
        return self._read("contrib")

    def load_investment_returns(self) -> pd.DataFrame:
        """加载表4。"""
        return self._read("returns")

    def load_withdrawal_behavior(self) -> pd.DataFrame:
        """加载表5。"""
        return self._read("withdrawal")

    def load_population(self) -> Optional[pd.DataFrame]:
        """加载表2（若存在）。"""
        path = self.data_dir / TABLE_FILES["population"]
        if path.exists():
            return pd.read_csv(path)
        return None


class DictDataSource(DataSource):
    """用内存字典/DataFrame 模拟数据，便于单元测试或无文件环境。

    Args:
        tables: 键为 core/contrib/returns/withdrawal(/population)，
            值为 DataFrame 或可转为 DataFrame 的记录列表。
    """

    def __init__(self, tables: Mapping[str, Any]) -> None:
        self._tables = {
            k: (v if isinstance(v, pd.DataFrame) else pd.DataFrame(v))
            for k, v in tables.items()
        }

    def _get(self, key: str) -> pd.DataFrame:
        if key not in self._tables:
            raise KeyError(f"DictDataSource 缺少表: {key}")
        return self._tables[key].copy()

    def load_core_parameters(self) -> pd.DataFrame:
        return self._get("core")

    def load_contributing_population(self) -> pd.DataFrame:
        return self._get("contrib")

    def load_investment_returns(self) -> pd.DataFrame:
        return self._get("returns")

    def load_withdrawal_behavior(self) -> pd.DataFrame:
        return self._get("withdrawal")

    def load_population(self) -> Optional[pd.DataFrame]:
        if "population" in self._tables:
            return self._get("population")
        return None


def set_reproducible_seed(seed: int = RANDOM_SEED) -> None:
    """固定 numpy 随机种子，保证可复现。"""
    np.random.seed(seed)


def get_aum0(core: pd.DataFrame, scenario: str = "中") -> float:
    """从表1读取制度总资产初值（亿港元）。

    Args:
        core: 表1 DataFrame。
        scenario: CSV 情景码。

    Returns:
        A_2026，单位亿港元。
    """
    mask = (core["参数名"] == "mpf_aum_total") & (core["情景"] == scenario)
    if not mask.any():
        mask = (core["参数名"] == "mpf_aum_total") & (core["情景"] == "中")
    if not mask.any():
        raise ValueError("表1缺少 mpf_aum_total")
    return float(core.loc[mask, "数值"].iloc[0])


def get_scalar_param(
    core: pd.DataFrame,
    name: str,
    scenario: str = "中",
    default: Optional[float] = None,
) -> float:
    """从表1读取标量参数。

    Args:
        core: 表1。
        name: 参数名。
        scenario: 情景码。
        default: 缺失时的默认值。

    Returns:
        参数数值。
    """
    mask = (core["参数名"] == name) & (core["情景"] == scenario)
    if not mask.any():
        mask = (core["参数名"] == name) & (core["情景"] == "中")
    if not mask.any():
        if default is not None:
            return float(default)
        raise ValueError(f"表1缺少参数: {name}")
    return float(core.loc[mask, "数值"].iloc[0])


def filter_scenario(df: pd.DataFrame, scenario: str) -> pd.DataFrame:
    """按情景过滤时序表，并按年份排序。"""
    out = df[df["情景"] == scenario].copy()
    if out.empty:
        raise ValueError(f"情景 {scenario!r} 在表中无数据")
    if "年份" in out.columns:
        out = out.sort_values("年份").reset_index(drop=True)
    return out


def load_model_inputs(
    source: Optional[DataSource] = None,
    data_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, pd.DataFrame]:
    """一次性加载模型所需全部表。

    Args:
        source: 自定义 DataSource；若为空则用 CSVDataSource(data_dir)。
        data_dir: CSV 目录（仅当 source 为空时生效）。

    Returns:
        字典：core / contrib / returns / withdrawal，以及可选 population。
    """
    set_reproducible_seed()
    ds = source if source is not None else CSVDataSource(data_dir)
    tables: Dict[str, pd.DataFrame] = {
        "core": ds.load_core_parameters(),
        "contrib": ds.load_contributing_population(),
        "returns": ds.load_investment_returns(),
        "withdrawal": ds.load_withdrawal_behavior(),
    }
    pop = ds.load_population()
    if pop is not None:
        tables["population"] = pop
    return tables
