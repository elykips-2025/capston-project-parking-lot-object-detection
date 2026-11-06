
import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]

DATASETS = [
    ("mapping-tests", "vacant"),
    ("occupied-tests", "occupied"),
]

LABELS = ("occupied", "vacant", "unknown")


def main():
    confusion = {
        actual: Counter()
        for actual in ("occupied", "vacant")
    }

    total = 0
    correct = 0
    classified = 0

    for dataset_name, actual in DATASETS:
        path = (
            BASE
            / "datasets"
            / dataset_name
            / "results"
            / "occupancy_results.json"
        )

        results = json.loads(path.read_text())

        print(f"\n{dataset_name.upper()}")

        for result in results:
            predicted = result["status"]

            if predicted not in LABELS:
                raise ValueError(
                    f"Unexpected prediction: {predicted}"
                )

            confusion[actual][predicted] += 1
            total += 1

            if predicted != "unknown":
                classified += 1

            if predicted == actual:
                correct += 1

            print(
                f"{result['bay_id']:4} "
                f"actual={actual:8} "
                f"predicted={predicted:8}"
            )

    print("\nCONFUSION MATRIX")
    print(f"{'Actual':12} {'Occupied':>10} {'Vacant':>10} {'Unknown':>10}")

    for actual, counts in confusion.items():
        print(
            f"{actual:12} "
            f"{counts['occupied']:>10} "
            f"{counts['vacant']:>10} "
            f"{counts['unknown']:>10}"
        )

    print("\nMETRICS")
    print(f"Total bays: {total}")
    print(f"Correct: {correct}")
    print(f"Coverage: {classified / total:.1%}")
    print(f"Overall accuracy: {correct / total:.1%}")
    print(
        "Accuracy on classified bays: "
        f"{correct / classified:.1%}"
        if classified else "No classified bays"
    )


if __name__ == "__main__":
    main()
