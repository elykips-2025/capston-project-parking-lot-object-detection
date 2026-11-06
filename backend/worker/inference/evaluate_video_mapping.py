import csv
from collections import Counter
from pathlib import Path

import cv2

from worker.inference.occupancy_classifier import OccupancyClassifier
from worker.inference.process_parking_frame import load_bays, process_frame

BASE = Path("datasets/video-mapping")
GROUND_TRUTH = BASE / "ground-truth.csv"
MAPPING = BASE / "parksight-bay-mapping.json"
FRAME = BASE / "reference-frame.jpg"
CHECKPOINT = Path("runs/occupancy/mobilenetv3_pilot/best.pt")


def main():
    with GROUND_TRUTH.open(newline="") as file:
        rows = list(csv.DictReader(file))

    truth = {row["bay_id"]: row for row in rows}
    assert len(rows) == len(truth) == 27
    assert all(
        row["ground_truth"] in {"empty", "occupied"}
        for row in rows
    )

    frame = cv2.imread(str(FRAME))
    if frame is None:
        raise FileNotFoundError(FRAME)

    classifier = OccupancyClassifier(str(CHECKPOINT))
    predictions = process_frame(
        frame,
        load_bays(str(MAPPING)),
        classifier,
    )

    results = []
    for prediction in predictions:
        bay_id = prediction["bay_id"]
        actual = truth[bay_id]["ground_truth"]
        predicted = prediction["state"]

        results.append({
            "bay_id": bay_id,
            "bay_type": truth[bay_id]["bay_type"],
            "actual": actual,
            "predicted": predicted,
            "correct": actual == predicted,
            "occupied_probability": prediction["occupied_probability"],
        })

    assert {r["bay_id"] for r in results} == set(truth)

    counts = Counter(r["predicted"] for r in results)
    classified = [
        r for r in results
        if r["predicted"] != "unknown"
    ]
    correct = sum(r["correct"] for r in classified)

    false_vacant = [
        r["bay_id"] for r in results
        if r["actual"] == "occupied"
        and r["predicted"] == "empty"
    ]

    print("\n--- Unknown Bay Diagnostics ---")

    for result in results:
        if result["predicted"] == "unknown":
            print(result)

    print(f"Total bays: {len(results)}")
    print(f"Occupied predictions: {counts['occupied']}")
    print(f"Empty predictions: {counts['empty']}")
    print(f"Unknown predictions: {counts['unknown']}")
    print(f"Correct classified: {correct}/{len(classified)}")
    print(f"Selective accuracy: {correct / len(classified):.2%}")
    print(f"Coverage: {len(classified) / len(results):.2%}")
    print(f"False vacancies: {false_vacant}")

    for bay_type in ("standard", "accessible"):
        subset = [r for r in results if r["bay_type"] == bay_type]
        available = sum(
            r["predicted"] == "empty" for r in subset
        )
        print(f"{bay_type} reported available: {available}")


if __name__ == "__main__":
    main()