# App 首页改版 A/B Test 实验效果分析

这是一个适合写入数据分析实习简历的完整 A/B Test 项目。项目模拟 App 首页改版实验，使用 Python 完成数据生成、清洗、指标计算、显著性检验、分群分析和可视化，并给出上线建议。

## 项目背景

产品团队对 App 首页进行了改版，希望通过更清晰的信息层级和更突出的行动按钮，提高用户点击和最终转化。实验将用户随机分为：

- `control`：使用旧版首页
- `treatment`：使用新版首页

核心问题是：新版首页是否显著提升 CTR 和 CVR，以及是否值得全量上线。

## 项目结构

```text
.
├── data/
│   ├── raw/ab_test_data.csv
│   └── processed/ab_test_clean.csv
├── outputs/
│   ├── figures/
│   │   ├── ctr_comparison.svg
│   │   ├── cvr_comparison.svg
│   │   ├── arpu_comparison.svg
│   │   ├── ctr_by_device.svg
│   │   └── cvr_by_source.svg
│   └── results/
│       ├── cleaning_report.csv
│       ├── group_metrics.csv
│       └── significance_tests.csv
├── notebooks/
│   └── app_homepage_ab_test_analysis.ipynb
├── scripts/
│   └── build_notebook.py
├── src/
│   ├── __init__.py
│   ├── generate_data.py
│   └── analyze_ab_test.py
├── requirements.txt
├── run_analysis.py
└── README.md
```

## 数据字段

| 字段 | 含义 |
|---|---|
| `user_id` | 用户唯一标识 |
| `group` | 实验组或对照组 |
| `impression` | 是否看到首页 |
| `click` | 是否发生点击 |
| `conversion` | 是否完成转化 |
| `payment` | 用户支付金额 |
| `device` | Android 或 iOS |
| `source` | 用户获客渠道 |

原始模拟数据包含 60,120 行，其中故意加入少量重复用户和缺失值，用于展示数据清洗能力。清洗后保留 59,920 名有效用户，每名用户仅保留一条记录。

## 分析方法

### 1. 数据清洗

- 检查必需字段是否齐全
- 删除重复 `user_id`
- 删除关键字段缺失记录
- 校验曝光、点击、转化字段为二元值
- 校验漏斗关系：`conversion <= click <= impression`
- 校验支付金额非负，未转化用户支付金额为 0

### 2. 核心指标

- **CTR（点击率）** = 点击人数 / 曝光人数
- **CVR（转化率）** = 转化人数 / 曝光人数
- **点击后 CVR** = 转化人数 / 点击人数
- **ARPU** = 总收入 / 用户数
- **相对提升率** = 实验组指标 / 对照组指标 - 1

### 3. 显著性检验

对 CTR 和 CVR 分别构建 2×2 列联表，使用 Pearson 卡方检验：

- 原假设 H0：实验组与对照组指标没有差异
- 备择假设 H1：实验组与对照组指标存在差异
- 显著性水平：`α = 0.05`
- 当 `p-value < 0.05` 时，认为差异具有统计显著性

## 如何运行

```bash
python run_analysis.py
```

也可以分步运行：

```bash
python src/generate_data.py
python src/analyze_ab_test.py
```

## Jupyter Notebook 展示版

面试和 GitHub 展示建议优先阅读 `notebooks/app_homepage_ab_test_analysis.ipynb`。Notebook 已保存执行结果，按项目背景、数据清洗、核心指标、卡方检验、分群分析和业务建议的顺序呈现完整分析过程。

更新数据或分析逻辑后，可重新生成并执行 Notebook：

```bash
python scripts/build_notebook.py
```

## 核心结论

本项目使用固定随机种子，结果可复现。详细结果保存在 `outputs/results/`：

| 指标 | 对照组 | 实验组 | 相对提升 | p-value | 是否显著 |
|---|---:|---:|---:|---:|---|
| CTR | 13.07% | 14.03% | +7.33% | 0.000618 | 是 |
| CVR | 2.55% | 3.21% | +25.89% | 0.000001 | 是 |
| ARPU | 1.189 | 1.515 | +27.44% | - | - |

- 新版首页对 CTR 和 CVR 的提升均达到统计显著，说明改版同时改善了用户互动与最终转化。
- 实验组 ARPU 高于对照组约 27.44%，说明改版带来了可观的收入增量。
- 在当前模拟实验条件下，建议逐步扩大新版流量，同时继续监控留存、退款率等护栏指标。

## 业务建议

1. 若 CTR 与 CVR 均显著提升，建议逐步扩大新版流量，并持续监控 ARPU、留存率和退款率等护栏指标。
2. 若 CTR 显著但 CVR 不显著，说明新版主要改善了点击吸引力，应继续优化点击后的转化路径。
3. 对不同设备和渠道采用分层策略，优先向提升明显的人群推广，同时针对弱势分群开展后续实验。
4. 上线前补充实验周期、样本量估算和新奇效应检查，避免短期波动造成误判。

## 简历表述示例

> 独立完成 App 首页改版 A/B Test 分析项目，使用 Python 清洗并分析 6 万条用户行为数据，搭建 CTR、CVR、ARPU 指标体系，通过卡方检验评估实验显著性，并结合设备与渠道分群定位增长机会，输出可视化报告与上线建议。

项目仅使用 Python 标准库，无需安装第三方依赖。
