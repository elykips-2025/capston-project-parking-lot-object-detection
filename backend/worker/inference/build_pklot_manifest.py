
import csv
import tarfile
from collections import Counter
from pathlib import Path

ARCHIVE = Path("datasets/pklot/PKLot.tar.gz")
OUTPUT = Path("datasets/pklot/pklot_manifest.csv")

CAMERAS = {"PUC", "UFPR04", "UFPR05"}
WEATHER = {"Sunny", "Cloudy", "Rainy"}
LABELS = {"Empty": 0, "Occupied": 1}

FIELDS = [
    "archive_path",
    "camera",
    "weather",
    "date",
    "label",
    "label_id",
    "filename",
]


def parse_member(name):
    parts = Path(name).parts

    # Expected:
    # PKLot/PKLotSegmented/PUC/Sunny/YYYY-MM-DD/Occupied/file.jpg
    if len(parts) != 7:
        return None

    root, section, camera, weather, date, label, filename = parts

    if root != "PKLot" or section != "PKLotSegmented":
        return None

    if camera not in CAMERAS:
        return None

    if weather not in WEATHER or label not in LABELS:
        return None

    if not filename.lower().endswith(".jpg"):
        return None

    return {
        "archive_path": name,
        "camera": camera,
        "weather": weather,
        "date": date,
        "label": label.lower(),
        "label_id": LABELS[label],
        "filename": filename,
    }


def main():
    if not ARCHIVE.is_file():
        raise FileNotFoundError(ARCHIVE)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    counts = Counter()
    skipped = 0

    with tarfile.open(ARCHIVE, "r:gz") as tar:
        with OUTPUT.open("w", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=FIELDS)
            writer.writeheader()

            for member in tar:
                if not member.isfile():
                    continue

                row = parse_member(member.name)

                if row is None:
                    skipped += 1
                    continue

                writer.writerow(row)
                counts[(row["camera"], row["label"])] += 1

    print(f"Manifest: {OUTPUT}")
    print(f"Total images: {sum(counts.values()):,}")
    print(f"Skipped files: {skipped:,}")

    for camera in sorted(CAMERAS):
        empty = counts[(camera, "empty")]
        occupied = counts[(camera, "occupied")]

        print(
            f"{camera}: "
            f"empty={empty:,}, "
            f"occupied={occupied:,}, "
            f"total={empty + occupied:,}"
        )


if __name__ == "__main__":
    main()
