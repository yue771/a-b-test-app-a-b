"""Clean, analyze, test, and visualize the app homepage A/B experiment."""

import csv
from collections import defaultdict
from html import escape
from math import erfc, sqrt
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_PATH = ROOT_DIR / "data" / "raw" / "ab_test_data.csv"
CLEAN_DATA_PATH = ROOT_DIR / "data" / "processed" / "ab_test_clean.csv"
RESULTS_DIR = ROOT_DIR / "outputs" / "results"
FIGURES_DIR = ROOT_DIR / "outputs" / "figures"
FIELDS = ["user_id", "group", "impression", "click", "conversion", "payment", "device", "source"]


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def clean_data(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Remove duplicates, missing values, and invalid funnel records."""
    seen_users = set()
    clean_rows = []
    duplicate_count = missing_count = invalid_count = 0

    for row in rows:
        if row["user_id"] in seen_users:
            duplicate_count += 1
            continue
        seen_users.add(row["user_id"])
        if any(not row[field] for field in FIELDS):
            missing_count += 1
            continue
        try:
            impression, click, conversion = (int(row[name]) for name in ["impression", "click", "conversion"])
            payment = float(row["payment"])
        except ValueError:
            invalid_count += 1
            continue
        valid = (
            row["group"] in {"control", "treatment"}
            and {impression, click, conversion} <= {0, 1}
            and conversion <= click <= impression
            and payment >= 0
            and (conversion == 1 or payment == 0)
        )
        if not valid:
            invalid_count += 1
            continue
        row.update({"impression": impression, "click": click, "conversion": conversion, "payment": payment})
        clean_rows.append(row)

    report = [
        {"item": "raw_rows", "value": len(rows)},
        {"item": "duplicate_user_rows", "value": duplicate_count},
        {"item": "rows_with_missing_values", "value": missing_count},
        {"item": "invalid_rows", "value": invalid_count},
        {"item": "clean_rows", "value": len(clean_rows)},
    ]
    return clean_rows, report


def aggregate(rows: list[dict], key_fields: list[str]) -> list[dict]:
    """Aggregate experiment metrics for any requested dimensions."""
    grouped = defaultdict(lambda: {"users": 0, "impressions": 0, "clicks": 0, "conversions": 0, "revenue": 0.0})
    for row in rows:
        key = tuple(row[field] for field in key_fields)
        bucket = grouped[key]
        bucket["users"] += 1
        bucket["impressions"] += row["impression"]
        bucket["clicks"] += row["click"]
        bucket["conversions"] += row["conversion"]
        bucket["revenue"] += row["payment"]

    results = []
    for key, values in sorted(grouped.items()):
        record = dict(zip(key_fields, key))
        record.update(values)
        record["revenue"] = round(record["revenue"], 2)
        record["ctr"] = record["clicks"] / record["impressions"]
        record["cvr"] = record["conversions"] / record["impressions"]
        record["post_click_cvr"] = record["conversions"] / record["clicks"]
        record["arpu"] = record["revenue"] / record["users"]
        results.append(record)
    return results


def chi_square_2x2(success_a: int, total_a: int, success_b: int, total_b: int) -> dict:
    """Run Pearson's chi-square test for a 2x2 table (df=1)."""
    observed = [[success_a, total_a - success_a], [success_b, total_b - success_b]]
    row_totals = [sum(row) for row in observed]
    col_totals = [sum(observed[row][col] for row in range(2)) for col in range(2)]
    grand_total = sum(row_totals)
    expected = [[row_totals[row] * col_totals[col] / grand_total for col in range(2)] for row in range(2)]
    chi2 = sum((observed[row][col] - expected[row][col]) ** 2 / expected[row][col] for row in range(2) for col in range(2))
    return {"chi_square": chi2, "p_value": erfc(sqrt(chi2 / 2))}


def run_significance_tests(metrics: list[dict]) -> list[dict]:
    """Test whether treatment CTR and CVR differ significantly from control."""
    groups = {row["group"]: row for row in metrics}
    tests = []
    for metric_name, success_col in [("CTR", "clicks"), ("CVR", "conversions")]:
        control, treatment = groups["control"], groups["treatment"]
        result = chi_square_2x2(control[success_col], control["impressions"], treatment[success_col], treatment["impressions"])
        control_rate = control[success_col] / control["impressions"]
        treatment_rate = treatment[success_col] / treatment["impressions"]
        tests.append(
            {
                "metric": metric_name,
                "control_rate": control_rate,
                "treatment_rate": treatment_rate,
                "absolute_lift": treatment_rate - control_rate,
                "relative_lift": treatment_rate / control_rate - 1,
                **result,
                "significant_at_0.05": result["p_value"] < 0.05,
            }
        )
    return tests


def create_bar_chart(path: Path, title: str, series: list[tuple[str, float, str]], percent: bool = True) -> None:
    """Create a lightweight SVG bar chart without third-party libraries."""
    width, height, margin = 900, 520, 80
    plot_height = height - 2 * margin
    max_value = max(value for _, value, _ in series) * 1.25
    bar_width = min(110, (width - 2 * margin) / (len(series) * 1.8))
    gap = (width - 2 * margin) / len(series)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#ffffff"/>',
             f'<text x="{width / 2}" y="38" text-anchor="middle" font-family="Arial" font-size="22" font-weight="bold">{escape(title)}</text>',
             f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="#94a3b8"/>']
    for index, (label, value, color) in enumerate(series):
        x = margin + gap * index + (gap - bar_width) / 2
        bar_height = value / max_value * plot_height
        y = height - margin - bar_height
        value_label = f"{value:.2%}" if percent else f"${value:.3f}"
        parts.extend([
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" rx="5" fill="{color}"/>',
            f'<text x="{x + bar_width/2:.1f}" y="{y - 10:.1f}" text-anchor="middle" font-family="Arial" font-size="16">{value_label}</text>',
            f'<text x="{x + bar_width/2:.1f}" y="{height-margin+25}" text-anchor="middle" font-family="Arial" font-size="14">{escape(label)}</text>',
        ])
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def plot_results(rows: list[dict], metrics: list[dict]) -> None:
    """Generate core and segmented SVG charts."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    groups = {row["group"]: row for row in metrics}
    colors = {"control": "#64748B", "treatment": "#2563EB"}
    for field, title, percent in [("ctr", "CTR: Control vs Treatment", True), ("cvr", "CVR: Control vs Treatment", True), ("arpu", "ARPU: Control vs Treatment", False)]:
        series = [(group.title(), groups[group][field], colors[group]) for group in ["control", "treatment"]]
        create_bar_chart(FIGURES_DIR / f"{field}_comparison.svg", title, series, percent)

    for dimension, field, title, filename in [
        ("device", "ctr", "CTR by Device and Group", "ctr_by_device.svg"),
        ("source", "cvr", "CVR by Source and Group", "cvr_by_source.svg"),
    ]:
        segmented = aggregate(rows, [dimension, "group"])
        series = [(f"{row[dimension]} - {row['group']}", row[field], colors[row["group"]]) for row in segmented]
        create_bar_chart(FIGURES_DIR / filename, title, series)


def main() -> None:
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError("Run `python src/generate_data.py` before analysis.")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rows, cleaning_report = clean_data(read_csv(RAW_DATA_PATH))
    metrics = aggregate(rows, ["group"])
    significance_tests = run_significance_tests(metrics)
    plot_results(rows, metrics)

    write_csv(CLEAN_DATA_PATH, rows, FIELDS)
    write_csv(RESULTS_DIR / "cleaning_report.csv", cleaning_report)
    write_csv(RESULTS_DIR / "group_metrics.csv", metrics)
    write_csv(RESULTS_DIR / "significance_tests.csv", significance_tests)
    print("Analysis complete.")
    for result in significance_tests:
        print(f"{result['metric']}: lift={result['relative_lift']:.2%}, p-value={result['p_value']:.6f}")


if __name__ == "__main__":
    main()
