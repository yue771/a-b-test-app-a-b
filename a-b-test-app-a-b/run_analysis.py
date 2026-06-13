"""Run the full reproducible A/B test project pipeline."""

from src.analyze_ab_test import main as analyze
from src.generate_data import main as generate


if __name__ == "__main__":
    generate()
    analyze()

