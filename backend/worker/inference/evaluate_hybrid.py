
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]

DATASETS = {
    "mapping-tests": "vacant",
    "occupied-tests": "occupied",
}


def hybrid(masked, unmasked):
    if "occupied" in (masked, unmasked):
        return "occupied"

    if masked == "vacant" and unmasked == "vacant":
        return "vacant"

    return "unknown"


def main():
    confusion = {
        actual: {"occupied": 0, "vacant": 0, "unknown": 0}
        for actual in ("occupied", "vacant")
    }

    for dataset, actual in DATASETS.items():
        directory = BASE / "datasets" / dataset / "results"

        masked = {
            item["bay_id"]: item
            for item in json.loads(
                (directory / "occupancy_results.json").read_text()
            )
        }

        unmasked = {
            item["bay_id"]: item
            for item in json.loads(
                (directory / "occupancy_unmasked.json").read_text()
            )
        }

        if masked.keys() != unmasked.keys():
            raise ValueError(f"Bay mismatch in {dataset}")

        print(f"\n{dataset.upper()}")

        for bay_id, original in masked.items():
            a = original["status"]
            b = unmasked[bay_id]["status"]
            result = hybrid(a, b)

            confusion[actual][result] += 1

            print(
                f"{bay_id}: masked={a:8} "
                f"unmasked={b:8} hybrid={result}"
            )

    total = sum(sum(row.values()) for row in confusion.values())
    correct = sum(confusion[label][label] for label in DATASETS.values())
    classified = total - sum(row["unknown"] for row in confusion.values())

    print("\nCONFUSION MATRIX")
    print(f"{'Actual':12} {'Occupied':>10} {'Vacant':>10} {'Unknown':>10}")

    for actual, row in confusion.items():
        print(
            f"{actual:12} "
            f"{row['occupied']:>10} "
            f"{row['vacant']:>10} "
            f"{row['unknown']:>10}"
        )

    print("\nMETRICS")
    print(f"Overall accuracy: {correct / total:.1%}")
    print(f"Coverage: {classified / total:.1%}")
    print(
        f"Classified accuracy: {correct / classified:.1%}"
        if classified else "Classified accuracy: N/A"
    )
    print(
        "False-vacant predictions: "
        f"{confusion['occupied']['vacant']}"
    )


if __name__ == "__main__":
    main()
