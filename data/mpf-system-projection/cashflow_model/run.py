# -*- coding: utf-8 -*-
"""主运行入口：加载 Prompt 1-1 数据，跑通三情景，写出 output/*.csv。

用法:
    python run.py
    python run.py --data-dir ..
    python run.py --start 2026 --end 2056

输出（默认 output/）:
    annual_悲观.csv / annual_基准.csv / annual_乐观.csv
    annual_all_scenarios.csv
    summary_comparison.csv
    asset_path_wide.csv
    inflection_depletion.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from data_loader import CSVDataSource, DictDataSource, set_reproducible_seed
from model import (
    MPFCashflowModel,
    ProjectionResult,
    compare_scenarios,
    wide_asset_path,
)
from scenarios import RANDOM_SEED, SCENARIO_MAP, list_scenarios


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    """解析命令行参数。"""
    p = argparse.ArgumentParser(description="强积金制度总账户 30 年现金流预测")
    p.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Prompt 1-1 CSV 目录（默认：本包上级 mpf-system-projection/）",
    )
    p.add_argument("--start", type=int, default=2026, help="起始年（含）")
    p.add_argument("--end", type=int, default=2056, help="终点年（含，期末资产年份）")
    p.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="结果输出目录（默认：本包下 output/）",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=RANDOM_SEED,
        help=f"随机种子（默认 {RANDOM_SEED}）",
    )
    return p.parse_args(argv)


def build_inflection_table(results: Dict[str, ProjectionResult]) -> pd.DataFrame:
    """汇总各情景拐点与耗尽年。"""
    rows = []
    for code, res in results.items():
        rows.append(
            {
                "情景": code,
                "情景标签": res.scenario_label,
                "资产下降拐点年份": res.summary.get("资产下降拐点年份"),
                "资产耗尽年份": res.summary.get("资产耗尽年份"),
                "投影期内资产始终上升": res.summary.get("投影期内资产始终上升"),
                "峰值资产_亿港元": res.summary.get("峰值资产_亿港元"),
                "峰值年份": res.summary.get("峰值年份"),
                "期末资产_亿港元": res.summary.get("期末资产_亿港元"),
            }
        )
    return pd.DataFrame(rows)


def print_example_output(results: Dict[str, ProjectionResult], comparison: pd.DataFrame) -> None:
    """向控制台打印示例输出摘要。"""
    print("=" * 64)
    print("强积金制度总账户 · 30 年现金流预测（示例输出）")
    print("=" * 64)
    print("\n【三情景对比摘要】")
    cols = [
        "情景标签",
        "初值资产_亿港元",
        "期末资产_亿港元",
        "累计供款_亿港元",
        "累计提取_亿港元",
        "资产下降拐点年份",
        "资产耗尽年份",
    ]
    show = comparison[[c for c in cols if c in comparison.columns]]
    print(show.to_string(index=False))

    base = results.get("中") or next(iter(results.values()))
    print(f"\n【基准情景 · 首尾各 3 年】（单位：亿港元）")
    preview_cols = [
        "年份",
        "总资产_期初_亿港元",
        "加权净回报率",
        "总供款_亿港元",
        "总提取_亿港元",
        "净现金流_亿港元",
        "总资产_期末_亿港元",
    ]
    annual = base.annual
    head = annual[preview_cols].head(3)
    tail = annual[preview_cols].tail(3)
    print(pd.concat([head, tail], ignore_index=True).to_string(index=False))
    print(
        f"\n拐点={base.summary.get('资产下降拐点年份')} | "
        f"耗尽={base.summary.get('资产耗尽年份')} | "
        f"2056 末资产≈{base.summary.get('期末资产_亿港元')}"
    )


def main(argv: Optional[list] = None) -> int:
    """主流程：加载 → 三情景投影 → 写 CSV → 打印摘要。"""
    args = parse_args(argv)
    set_reproducible_seed(args.seed)

    pkg_dir = Path(__file__).resolve().parent
    out_dir = Path(args.output_dir) if args.output_dir else pkg_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 预留：若需 Dict 模拟，可改为 DictDataSource(tables=...)
    source = CSVDataSource(args.data_dir)
    model = MPFCashflowModel(
        source=source,
        start_year=args.start,
        end_year=args.end,
    )

    results = model.run_all()
    comparison = compare_scenarios(results)
    asset_wide = wide_asset_path(results)
    inflection = build_inflection_table(results)

    # 逐年明细（分情景 + 合并）
    all_annual = []
    for code, res in results.items():
        label = res.scenario_label
        path = out_dir / f"annual_{label}.csv"
        res.annual.to_csv(path, index=False, encoding="utf-8-sig")
        all_annual.append(res.annual)
        print(f"已写入 {path}")

    pd.concat(all_annual, ignore_index=True).to_csv(
        out_dir / "annual_all_scenarios.csv", index=False, encoding="utf-8-sig"
    )
    comparison.to_csv(
        out_dir / "summary_comparison.csv", index=False, encoding="utf-8-sig"
    )
    asset_wide.to_csv(
        out_dir / "asset_path_wide.csv", index=False, encoding="utf-8-sig"
    )
    inflection.to_csv(
        out_dir / "inflection_depletion.csv", index=False, encoding="utf-8-sig"
    )

    print(f"\n情景映射: {SCENARIO_MAP} | 可用: {list_scenarios()}")
    print(f"随机种子: {args.seed}")
    print(f"输出目录: {out_dir}")
    print_example_output(results, comparison)
    return 0


if __name__ == "__main__":
    sys.exit(main())
