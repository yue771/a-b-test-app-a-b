"""Generate a reproducible synthetic dataset for an app homepage A/B test."""

import csv
import random
from pathlib import Path


SEED = 20260612
N_USERS = 60_000
ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_PATH = ROOT_DIR / "data" / "raw" / "ab_test_data.csv"
FIELDS = ["user_id", "group", "impression", "click", "conversion", "payment", "device", "source"]


def weighted_choice(rng: random.Random, choices: list[tuple[str, float]]) -> str:
    """Choose one label based on cumulative weights."""
    point = rng.random()
    cumulative = 0.0
    for label, weight in choices:
        cumulative += weight
        if point < cumulative:
            return label
    return choices[-1][0]


def generate_ab_test_data(n_users: int = N_USERS, seed: int = SEED) -> list[dict]:
    """Create user-level A/B test data with realistic funnel relationships."""
    rng = random.Random(seed)
    rows = []
    for user_number in range(1, n_users + 1):
        group = weighted_choice(rng, [("control", 0.5), ("treatment", 0.5)])
        device = weighted_choice(rng, [("Android", 0.58), ("iOS", 0.42)])
        source = weighted_choice(
            rng,
            [("organic", 0.42), ("paid_search", 0.27), ("social", 0.20), ("referral", 0.11)],
        )

        click_probability = (
            0.118
            + (0.008 if device == "iOS" else 0)
            + {"organic": 0, "paid_search": 0.014, "social": 0.006, "referral": 0.010}[source]
            + (0.012 if group == "treatment" else 0)
        )
        click = int(rng.random() < click_probability)
        post_click_cvr = 0.205 + (0.010 if device == "iOS" else -0.004)
        post_click_cvr += 0.018 if group == "treatment" else 0
        conversion = int(click == 1 and rng.random() < post_click_cvr)
        payment = round(rng.gammavariate(2.6, 18.0), 2) if conversion else 0.0

        rows.append(
            {
                "user_id": f"U{user_number:06d}",
                "group": group,
                "impression": 1,
                "click": click,
                "conversion": conversion,
                "payment": payment,
                "device": device,
                "source": source,
            }
        )

    # Add documented data quality issues so the cleaning step is meaningful.
    rows.extend(dict(row) for row in rng.sample(rows, 120))
    for row in rng.sample(rows, 80):
        row[rng.choice(["device", "source"])] = ""
    rng.shuffle(rows)
    return rows


def main() -> None:
    RAW_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = generate_ab_test_data()
    with RAW_DATA_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated {len(rows):,} rows at {RAW_DATA_PATH}")


if __name__ == "__main__":
    main()

