
import csv
import random
from collections import Counter, defaultdict
from pathlib import Path

INPUT = Path("datasets/pklot/pklot_manifest.csv")
OUTPUT = Path("datasets/pklot/pklot_splits.csv")

SEED = 42
TRAIN_RATIO = 0.8
TEST_CAMERA = "UFPR05"


def main():
    rows = []

    with INPUT.open(newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames

        for row in reader:
            rows.append(row)

    if not fieldnames:
        raise ValueError("Manifest is empty")

    # Group by camera and acquisition date.
    dates_by_camera = defaultdict(set)

    for row in rows:
        if row["camera"] != TEST_CAMERA:
            dates_by_camera[row["camera"]].add(row["date"])

    rng = random.Random(SEED)
    training_dates = {}

    for camera, dates in sorted(dates_by_camera.items()):
        ordered = sorted(dates)
        rng.shuffle(ordered)

        split_index = int(len(ordered) * TRAIN_RATIO)

        if len(ordered) >= 2:
            split_index = max(1, min(split_index, len(ordered) - 1))

        training_dates[camera] = set(ordered[:split_index])

        print(
            f"{camera}: "
            f"{len(training_dates[camera])} train dates, "
            f"{len(ordered) - len(training_dates[camera])} validation dates"
        )

    counts = Counter()

    with OUTPUT.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames + ["split"],
        )
        writer.writeheader()

        for row in rows:
            if row["camera"] == TEST_CAMERA:
                split = "test"
            elif row["date"] in training_dates[row["camera"]]:
                split = "train"
            else:
                split = "val"

            writer.writerow({**row, "split": split})
            counts[(split, row["label"])] += 1

    print(f"\nOutput: {OUTPUT}")

    for split in ("train", "val", "test"):
        empty = counts[(split, "empty")]
        occupied = counts[(split, "occupied")]

        print(
            f"{split}: "
            f"empty={empty:,}, "
            f"occupied={occupied:,}, "
            f"total={empty + occupied:,}"
        )


if __name__ == "__main__":
    main()
