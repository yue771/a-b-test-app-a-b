"""Build and execute the portfolio-facing A/B test analysis notebook."""

import contextlib
import io
import json
import traceback
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "notebooks" / "app_homepage_ab_test_analysis.ipynb"


def markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


cells = [
    markdown(
        """# App 首页改版 A/B Test 实验效果分析

## 项目目标

产品团队希望判断新版 App 首页是否能够提升用户互动和最终转化。本分析将用户随机分为旧版首页对照组（Control）和新版首页实验组（Treatment），重点回答：

1. 新版首页是否提升了点击率（CTR）？
2. 新版首页是否提升了整体转化率（CVR）？
3. 指标提升是否具有统计显著性？
4. 不同设备和获客渠道的实验效果是否一致？

**决策标准：** 对 CTR 和 CVR 使用 Pearson 卡方检验，显著性水平设为 `α = 0.05`。
"""
    ),
    markdown(
        """## 1. 加载数据与分析函数

Notebook 复用 `src/analyze_ab_test.py` 中的清洗、指标计算与卡方检验函数，使展示结果与正式分析流程保持一致。
"""
    ),
    code(
        """from pathlib import Path
import sys

ROOT = Path.cwd()
if not (ROOT / "src").exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src.analyze_ab_test import read_csv, clean_data, aggregate, run_significance_tests

RAW_DATA_PATH = ROOT / "data" / "raw" / "ab_test_data.csv"
rows = read_csv(RAW_DATA_PATH)
print(f"原始数据行数: {len(rows):,}")
print(f"字段: {', '.join(rows[0].keys())}")
print("\\n前 3 条数据:")
for row in rows[:3]:
    print(row)
"""
    ),
    markdown(
        """## 2. 数据清洗与质量检查

清洗规则包括：删除重复用户、删除关键字段缺失记录、校验二元事件字段、校验 `conversion <= click <= impression` 漏斗关系，以及检查支付金额。
"""
    ),
    code(
        """clean_rows, cleaning_report = clean_data(rows)
print("数据清洗报告")
for item in cleaning_report:
    print(f"{item['item']:<26} {item['value']:>8,}")

print(f"\\n数据保留率: {len(clean_rows) / len(rows):.2%}")
"""
    ),
    markdown(
        """## 3. 核心指标计算

- **CTR** = 点击人数 / 曝光人数
- **CVR** = 转化人数 / 曝光人数
- **点击后 CVR** = 转化人数 / 点击人数
- **ARPU** = 总收入 / 用户数
"""
    ),
    code(
        """group_metrics = aggregate(clean_rows, ["group"])
print(f"{'Group':<12}{'Users':>9}{'CTR':>10}{'CVR':>10}{'Post-click CVR':>18}{'ARPU':>10}")
print("-" * 69)
for row in group_metrics:
    print(
        f"{row['group']:<12}{row['users']:>9,}{row['ctr']:>10.2%}"
        f"{row['cvr']:>10.2%}{row['post_click_cvr']:>18.2%}{row['arpu']:>10.3f}"
    )
"""
    ),
    markdown(
        """## 4. 卡方显著性检验

对 CTR 和 CVR 分别构建 2×2 列联表：

- **H0（原假设）：** 实验组与对照组指标不存在差异
- **H1（备择假设）：** 实验组与对照组指标存在差异
- 当 `p-value < 0.05` 时拒绝原假设，认为差异具有统计显著性
"""
    ),
    code(
        """test_results = run_significance_tests(group_metrics)
print(f"{'Metric':<10}{'Control':>11}{'Treatment':>12}{'Rel. Lift':>12}{'Chi-square':>13}{'p-value':>13}{'Significant':>13}")
print("-" * 84)
for row in test_results:
    print(
        f"{row['metric']:<10}{row['control_rate']:>11.2%}{row['treatment_rate']:>12.2%}"
        f"{row['relative_lift']:>12.2%}{row['chi_square']:>13.3f}"
        f"{row['p_value']:>13.6f}{str(row['significant_at_0.05']):>13}"
    )
"""
    ),
    markdown(
        """## 5. 核心指标可视化

### CTR 对比
![CTR comparison](../outputs/figures/ctr_comparison.svg)

### CVR 对比
![CVR comparison](../outputs/figures/cvr_comparison.svg)

### ARPU 对比
![ARPU comparison](../outputs/figures/arpu_comparison.svg)
"""
    ),
    markdown(
        """## 6. 分群分析

分群分析用于判断总体提升是否由少数人群驱动，并识别后续优化机会。这里分别观察设备 CTR 和渠道 CVR。
"""
    ),
    code(
        """device_metrics = aggregate(clean_rows, ["device", "group"])
source_metrics = aggregate(clean_rows, ["source", "group"])

print("设备 CTR")
for row in device_metrics:
    print(f"{row['device']:<10} {row['group']:<10} CTR={row['ctr']:.2%}  users={row['users']:,}")

print("\\n渠道 CVR")
for row in source_metrics:
    print(f"{row['source']:<13} {row['group']:<10} CVR={row['cvr']:.2%}  users={row['users']:,}")
"""
    ),
    markdown(
        """### 分群可视化

![CTR by device](../outputs/figures/ctr_by_device.svg)

![CVR by source](../outputs/figures/cvr_by_source.svg)
"""
    ),
    markdown(
        """## 7. 核心结论与业务建议

### 核心结论

- 实验组 CTR 从 **13.07%** 提升至 **14.03%**，相对提升 **7.33%**，`p = 0.000618`，具有统计显著性。
- 实验组 CVR 从 **2.55%** 提升至 **3.21%**，相对提升 **25.89%**，`p < 0.00001`，具有统计显著性。
- 实验组 ARPU 从 **1.189** 提升至 **1.515**，相对提升约 **27.44%**。
- 改版同时改善点击、转化和收入表现，结果并非只停留在浅层互动指标。

### 业务建议

1. 建议逐步扩大新版首页流量，而不是立即一次性全量上线。
2. 扩量期间持续监控留存率、退款率、页面加载速度等护栏指标。
3. 针对设备和渠道继续开展分层实验，验证不同人群的长期效果。
4. 正式业务实验中应补充实验周期检查、样本量估算和新奇效应评估。

### 面试表达

> 使用 Python 清洗并分析 6 万条 App 用户行为数据，搭建 CTR、CVR、ARPU 指标体系；通过卡方检验验证首页改版使 CTR、CVR 分别显著提升 7.33% 和 25.89%，结合设备及渠道分群输出渐进式上线建议。
"""
    ),
]

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}


def execute_code_cells() -> None:
    namespace = {"__name__": "__notebook__"}
    execution_count = 0
    old_cwd = Path.cwd()
    try:
        import os

        os.chdir(ROOT)
        for cell in notebook["cells"]:
            if cell["cell_type"] != "code":
                continue
            execution_count += 1
            stream = io.StringIO()
            cell["execution_count"] = execution_count
            try:
                with contextlib.redirect_stdout(stream):
                    exec("".join(cell["source"]), namespace)
                text = stream.getvalue()
                if text:
                    cell["outputs"] = [{"name": "stdout", "output_type": "stream", "text": text.splitlines(keepends=True)}]
            except Exception:
                cell["outputs"] = [{
                    "ename": "ExecutionError",
                    "evalue": "Notebook cell failed",
                    "output_type": "error",
                    "traceback": traceback.format_exc().splitlines(),
                }]
                raise
    finally:
        os.chdir(old_cwd)


execute_code_cells()
NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
NOTEBOOK_PATH.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Built and executed {NOTEBOOK_PATH}")
