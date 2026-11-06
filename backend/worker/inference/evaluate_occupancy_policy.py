
import csv
from collections import Counter
from pathlib import Path

INPUT = Path(
    "runs/occupancy/mobilenetv3_pilot/external_results.csv"
)

OUTPUT = Path(
    "runs/occupancy/mobilenetv3_pilot/policy_results.csv"
)

EMPTY_THRESHOLD = 0.10
OCCUPIED_THRESHOLD = 0.90


def classify(occupied_probability):
    if occupied_probability >= OCCUPIED_THRESHOLD:
        return "occupied"

    if occupied_probability <= EMPTY_THRESHOLD:
        return "empty"

    return "unknown"


def main():
    with INPUT.open(newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError("No evaluation results found")

    counts = Counter()

    for row in rows:
        probability = float(row["occupied_probability"])
        actual = row["actual"]

        if not 0 <= probability <= 1:
            raise ValueError("Invalid occupied probability")

        state = classify(probability)

        row["operational_state"] = state
        row["available"] = state == "empty"

        counts[state] += 1

        if state == "unknown":
            counts["abstained"] += 1
        elif state == actual:
            counts["correct"] += 1
        else:
            counts["incorrect"] += 1

        if actual == "occupied" and state == "empty":
            counts["false_vacant"] += 1

    total = len(rows)
    classified = total - counts["abstained"]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)

    print("\nParkSight occupancy policy evaluation")
    print("-----------------------------------")
    print(f"Total bays: {total}")
    print(f"Occupied: {counts['occupied']}")
    print(f"Empty: {counts['empty']}")
    print(f"Unknown: {counts['unknown']}")
    print(f"False vacancies: {counts['false_vacant']}")

    print(f"\nCoverage: {classified / total:.2%}")
    print(f"Abstention rate: {counts['abstained'] / total:.2%}")

    if classified:
        print(
            f"Selective accuracy: "
            f"{counts['correct'] / classified:.2%}"
        )

    print("\nIndividual decisions:")
    for row in rows:
        print(
            f"{row['bay']:<23} "
            f"actual={row['actual']:<8} "
            f"state={row['operational_state']:<8} "
            f"p_occupied={float(row['occupied_probability']):.4f}"
        )

    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    main()
