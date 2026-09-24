# -*- coding: utf-8 -*-
"""核心现金流计算：A_{t+1} = A_t·(1+r_t) + C_t − W_t − E_t。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from data_loader import (
    DataSource,
    filter_scenario,
    get_aum0,
    get_scalar_param,
    load_model_inputs,
)
from scenarios import ScenarioParams, get_scenario


# 有关入息法定上下限（港元/月）；表1亦可覆盖
Y_MIN_DEFAULT = 7100.0
Y_MAX_DEFAULT = 30000.0
ALPHA_EE = 0.05
ALPHA_ER = 0.05
ALPHA_SE = 0.05

# 单位换算：
#   提取：万人 × 万港元 = 亿港元
#   供款：缴费人数以「万人」计时，
#         C(亿) = N_万人 × 月入(港元) × 12 × 费率 / 1e4
#         （等价于 N_人=N_万人×1e4 后再 /1e8）
CONTRIB_YI_SCALE = 1e4


@dataclass
class ProjectionResult:
    """单情景投影结果容器。"""

    scenario_csv: str
    scenario_label: str
    annual: pd.DataFrame
    summary: Dict[str, object] = field(default_factory=dict)

    @property
    def depletion_year(self) -> Optional[int]:
        """资产耗尽年份（期末资产 ≤ 0 的首年）；未耗尽则 None。"""
        v = self.summary.get("资产耗尽年份")
        return None if v in (None, "", "不适用") else int(v)

    @property
    def inflection_year(self) -> Optional[int]:
        """总资产开始下降的拐点年份（首个 A_{t+1}<A_t 的 t+1）。"""
        v = self.summary.get("资产下降拐点年份")
        return None if v in (None, "", "不适用") else int(v)


class MPFCashflowModel:
    """强积金制度总账户现金流预测模型。

    计息惯例：期初存量先计息，再加减当年流量（框架 §2）。
    """

    def __init__(
        self,
        tables: Optional[Dict[str, pd.DataFrame]] = None,
        source: Optional[DataSource] = None,
        data_dir: Optional[str] = None,
        start_year: int = 2026,
        end_year: int = 2056,
    ) -> None:
        """初始化模型。

        Args:
            tables: 已加载的表字典；与 source/data_dir 三选一优先。
            source: 可替换 DataSource（真实业务数据接口）。
            data_dir: Prompt 1-1 CSV 目录。
            start_year: 投影起始年（含）。
            end_year: 投影终止年（含），对应期末资产年份。
        """
        self.tables = tables if tables is not None else load_model_inputs(
            source=source, data_dir=data_dir
        )
        self.start_year = int(start_year)
        self.end_year = int(end_year)
        # 流量年份：start .. end-1，共 (end-start) 年；期末资产落在 end_year
        self.flow_years = list(range(self.start_year, self.end_year))

    # ------------------------------------------------------------------
    # 回报
    # ------------------------------------------------------------------
    def compute_weighted_return(
        self,
        year: int,
        scenario: str,
        year_index: int,
        cons_drift: float,
    ) -> Tuple[float, Dict[str, float]]:
        """计算系统加权净回报 r_t = Σ w_j·r_j，并可选配置滑移。

        Args:
            year: 日历年。
            scenario: CSV 情景码。
            year_index: 相对起始年的偏移（0,1,2,...）。
            cons_drift: 保守基金权重每年上调幅度。

        Returns:
            (r_t, 调整后权重字典)。
        """
        ret = self.tables["returns"]
        block = ret[(ret["年份"] == year) & (ret["情景"] == scenario)]
        if block.empty:
            raise ValueError(f"表4缺少 {year}/{scenario} 回报数据")

        # 原始权重与回报
        weights: Dict[str, float] = {}
        rates: Dict[str, float] = {}
        for _, row in block.iterrows():
            name = str(row["基金类型"])
            weights[name] = float(row["配置权重_中枢"])
            rates[name] = float(row["年率化净回报率"])

        # 老龄化配置滑移：保守类上升，其余按相对比例再归一（框架 §5.3）
        cons_key = "保守基金"
        if cons_key in weights and cons_drift != 0.0:
            w_cons = min(0.40, weights[cons_key] + cons_drift * year_index)
            others = {k: v for k, v in weights.items() if k != cons_key}
            rest_sum = sum(others.values())
            scale = (1.0 - w_cons) / rest_sum if rest_sum > 0 else 0.0
            weights = {k: v * scale for k, v in others.items()}
            weights[cons_key] = w_cons

        w_sum = sum(weights.values())
        if abs(w_sum - 1.0) > 1e-6:
            weights = {k: v / w_sum for k, v in weights.items()}

        r = sum(weights[k] * rates[k] for k in weights)
        return float(r), weights

    # ------------------------------------------------------------------
    # 供款
    # ------------------------------------------------------------------
    def compute_contributions(
        self,
        year: int,
        scenario: str,
        params: ScenarioParams,
    ) -> Dict[str, float]:
        """计算总供款 C_t 及其分项。

        启用规则引擎时：
            C = C_EE + C_ER + C_SE + C_vol
        其中处理低于下限（雇员免供、雇主仍缴）、上限封顶、自雇 5% 单边。

        Args:
            year: 日历年。
            scenario: CSV 情景码。
            params: 情景控制参数。

        Returns:
            分项与合计字典（亿港元）。
        """
        contrib = filter_scenario(self.tables["contrib"], scenario)
        row = contrib[contrib["年份"] == year]
        if row.empty:
            raise ValueError(f"表3缺少 {year}/{scenario}")
        row = row.iloc[0]

        n = float(row["缴费人数_万人"])  # 万人
        y_bar = float(row["平均有关入息_港元每月"])
        c_simple = float(row["年强制性供款流入_亿港元"])

        # 截断校验：有关入息应在 [ymin, ymax]
        core = self.tables["core"]
        y_min = get_scalar_param(core, "relevant_income_min_monthly", scenario, Y_MIN_DEFAULT)
        y_max = get_scalar_param(core, "relevant_income_max_monthly", scenario, Y_MAX_DEFAULT)
        y_bar = float(np.clip(y_bar, y_min, y_max))

        if not params.use_income_band_engine:
            c_forced = c_simple
            c_vol = params.kappa * c_forced
            return {
                "C_EE": np.nan,
                "C_ER": np.nan,
                "C_SE": np.nan,
                "C_forced": c_forced,
                "C_vol": c_vol,
                "C": c_forced + c_vol,
                "C_simple_table": c_simple,
                "N": n,
                "y_bar": y_bar,
            }

        # —— 规则引擎（框架 §3.3–3.5）——
        n_se = params.se_share * n
        n_ee = n - n_se
        pi = params.pi_low
        y_low = min(params.y_low, y_min)  # 低薪组应低于下限

        # 雇员：低于下限不供；其余对有关入息缴 5%
        # 万人 × 港元/月 × 12 × 费率 / 1e4 = 亿港元
        c_ee = n_ee * (1.0 - pi) * y_bar * 12.0 * ALPHA_EE / CONTRIB_YI_SCALE

        # 雇主：低薪组仍按实际工资（不超过 ymax）缴 5%；其余按 y_bar
        y_er_blend = (1.0 - pi) * y_bar + pi * min(y_low, y_max)
        c_er = n_ee * y_er_blend * 12.0 * ALPHA_ER / CONTRIB_YI_SCALE

        # 自雇：单边 5%，入息略折
        y_se = float(np.clip(params.se_income_factor * y_bar, y_min, y_max))
        c_se = n_se * y_se * 12.0 * ALPHA_SE / CONTRIB_YI_SCALE

        c_forced = c_ee + c_er + c_se
        c_vol = params.kappa * c_forced
        return {
            "C_EE": c_ee,
            "C_ER": c_er,
            "C_SE": c_se,
            "C_forced": c_forced,
            "C_vol": c_vol,
            "C": c_forced + c_vol,
            "C_simple_table": c_simple,
            "N": n,
            "y_bar": y_bar,
        }

    # ------------------------------------------------------------------
    # 提取
    # ------------------------------------------------------------------
    def compute_withdrawals(
        self,
        year: int,
        scenario: str,
        params: ScenarioParams,
        assets: float,
        n_contrib: float,
    ) -> Dict[str, float]:
        """计算总提取 W_t = W_age65 + W_early。

        Args:
            year: 日历年。
            scenario: CSV 情景码。
            params: 情景参数。
            assets: 期初总资产 A_t（亿港元），用于量级校验。
            n_contrib: 缴费人数（万人）。

        Returns:
            分项与合计（亿港元）。
        """
        wdf = filter_scenario(self.tables["withdrawal"], scenario)
        row = wdf[wdf["年份"] == year]
        if row.empty:
            raise ValueError(f"表5缺少 {year}/{scenario}")
        row = row.iloc[0]

        r_retire = float(row["退休人数_万人"])
        omega = float(row["平均提取比例"])
        b_retire = float(row["人均账户余额_万港元"])
        # 万人 × 万港元 × 比例 = 亿港元（勿再 /100）
        w65 = r_retire * b_retire * omega

        # 提前提取：强度 λ × 缴费人数 × 折算人均余额 × 全额提取
        b_early = params.early_balance_factor * b_retire
        lam = params.lambda_dep + params.lambda_incap + params.lambda_other
        w_early = lam * n_contrib * b_early  # 万人 × 万港元 = 亿港元

        w_total = w65 + w_early
        return {
            "W_age65": w65,
            "W_early": w_early,
            "W": w_total,
            "R_retire": r_retire,
            "omega": omega,
            "B_retire": b_retire,
            "W_over_A": (w_total / assets) if assets > 0 else np.nan,
        }

    # ------------------------------------------------------------------
    # 主递推
    # ------------------------------------------------------------------
    def run(self, scenario: str = "中") -> ProjectionResult:
        """运行单情景 30 年投影。

        Args:
            scenario: 「低/中/高」或「悲观/基准/乐观」。

        Returns:
            ProjectionResult，含逐年明细与摘要指标。
        """
        params = get_scenario(scenario)
        csv_code = params.csv_code
        core = self.tables["core"]

        a0 = get_aum0(core, "中") * params.aum0_scale  # 推荐共用真实锚点
        assets = float(a0)

        records: List[dict] = []
        # 先记录起始年期初资产（流量循环前）
        for i, year in enumerate(self.flow_years):
            r_t, weights = self.compute_weighted_return(
                year, csv_code, i, params.cons_weight_drift
            )
            c_parts = self.compute_contributions(year, csv_code, params)
            w_parts = self.compute_withdrawals(
                year, csv_code, params, assets, c_parts["N"]
            )

            # 行政费用：E_t = φ · A_t（表4已是净回报，不再扣投管费）
            e_t = params.phi * assets

            c_t = float(c_parts["C"])
            w_t = float(w_parts["W"])
            net_cf = c_t - w_t - e_t  # 未含投资损益的净现金流

            # 核心恒等式
            a_next = assets * (1.0 + r_t) + c_t - w_t - e_t

            records.append(
                {
                    "年份": year,
                    "情景": csv_code,
                    "情景标签": params.label,
                    "总资产_期初_亿港元": round(assets, 4),
                    "加权净回报率": round(r_t, 6),
                    "总供款_亿港元": round(c_t, 4),
                    "其中_雇员强制": round(float(c_parts["C_EE"]), 4)
                    if c_parts["C_EE"] == c_parts["C_EE"]
                    else np.nan,
                    "其中_雇主强制": round(float(c_parts["C_ER"]), 4)
                    if c_parts["C_ER"] == c_parts["C_ER"]
                    else np.nan,
                    "其中_自雇强制": round(float(c_parts["C_SE"]), 4)
                    if c_parts["C_SE"] == c_parts["C_SE"]
                    else np.nan,
                    "其中_自愿供款": round(float(c_parts["C_vol"]), 4),
                    "表3_强制流入对照": round(float(c_parts["C_simple_table"]), 4),
                    "总提取_亿港元": round(w_t, 4),
                    "其中_达龄提取": round(float(w_parts["W_age65"]), 4),
                    "其中_提前提取": round(float(w_parts["W_early"]), 4),
                    "费用_亿港元": round(e_t, 4),
                    "净现金流_亿港元": round(net_cf, 4),  # C-W-E
                    "投资损益_亿港元": round(assets * r_t, 4),
                    "总资产_期末_亿港元": round(a_next, 4),
                    "资产同比增速": round(a_next / assets - 1.0, 6) if assets > 0 else np.nan,
                    "供款占资产": round(c_t / assets, 6) if assets > 0 else np.nan,
                    "提取占资产": round(w_t / assets, 6) if assets > 0 else np.nan,
                    "缴费人数_万人": round(float(c_parts["N"]), 4),
                    "平均有关入息": round(float(c_parts["y_bar"]), 2),
                    "保守基金权重": round(weights.get("保守基金", np.nan), 4),
                }
            )
            assets = a_next
            # 若已耗尽，后续年份仍记录但资产钳制为 0，避免负资产无解释滚动
            if assets < 0:
                assets = 0.0

        annual = pd.DataFrame(records)
        summary = self._build_summary(annual, params, a0)
        return ProjectionResult(
            scenario_csv=csv_code,
            scenario_label=params.label,
            annual=annual,
            summary=summary,
        )

    def run_all(self) -> Dict[str, ProjectionResult]:
        """运行低/中/高三情景。"""
        return {code: self.run(code) for code in ("低", "中", "高")}

    @staticmethod
    def _build_summary(
        annual: pd.DataFrame,
        params: ScenarioParams,
        a0: float,
    ) -> Dict[str, object]:
        """识别拐点、耗尽年，并汇总关键指标。"""
        a_end_col = annual["总资产_期末_亿港元"]
        a_beg_col = annual["总资产_期初_亿港元"]

        # 下降拐点：首个期末 < 期初 的年份（资产开始下降的当年）
        inflection = None
        for _, row in annual.iterrows():
            if row["总资产_期末_亿港元"] < row["总资产_期初_亿港元"]:
                inflection = int(row["年份"])
                break

        # 资产耗尽：期末资产 ≤ 0 的首年
        depletion = None
        for _, row in annual.iterrows():
            if row["总资产_期末_亿港元"] <= 0:
                depletion = int(row["年份"])
                break

        last = annual.iloc[-1]
        return {
            "情景": params.csv_code,
            "情景标签": params.label,
            "初值资产_亿港元": round(a0, 2),
            "期末资产_亿港元": round(float(last["总资产_期末_亿港元"]), 2),
            "期末年份": int(last["年份"]) + 1,  # 流量年末 → 下一期初 = 投影终点
            "累计供款_亿港元": round(float(annual["总供款_亿港元"].sum()), 2),
            "累计提取_亿港元": round(float(annual["总提取_亿港元"].sum()), 2),
            "累计净现金流_亿港元": round(float(annual["净现金流_亿港元"].sum()), 2),
            "平均加权回报率": round(float(annual["加权净回报率"].mean()), 6),
            "资产下降拐点年份": inflection if inflection is not None else "不适用",
            "资产耗尽年份": depletion if depletion is not None else "不适用",
            "投影期内资产始终上升": inflection is None,
            "峰值资产_亿港元": round(float(max(a_beg_col.max(), a_end_col.max())), 2),
            "峰值年份": int(
                annual.loc[a_end_col.idxmax(), "年份"]
            )
            if len(annual)
            else None,
        }


def compare_scenarios(results: Dict[str, ProjectionResult]) -> pd.DataFrame:
    """将三情景摘要拼成对比表。"""
    rows = [res.summary for _, res in results.items()]
    return pd.DataFrame(rows)


def wide_asset_path(results: Dict[str, ProjectionResult]) -> pd.DataFrame:
    """输出宽表：年份 × 三情景资产路径（含起点与终点）。

    路径点 = 各年期初资产 + 最后一年流量后的期末资产（即投影终点年）。
    """
    out: Optional[pd.DataFrame] = None
    for _code, res in results.items():
        years = list(res.annual["年份"]) + [int(res.annual["年份"].iloc[-1]) + 1]
        assets = list(res.annual["总资产_期初_亿港元"]) + [
            float(res.annual["总资产_期末_亿港元"].iloc[-1])
        ]
        piece = pd.DataFrame({"年份": years, f"总资产_{res.scenario_label}": assets})
        out = piece if out is None else out.merge(piece, on="年份", how="outer")
    assert out is not None
    return out.sort_values("年份").reset_index(drop=True)
