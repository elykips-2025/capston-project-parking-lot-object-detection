
from collections import Counter
from pathlib import Path
from statistics import median

BASE = Path(__file__).resolve().parents[2]
DATASET = BASE / "datasets" / "parking-vehicles"

def main():
    for split in ("train", "valid", "test"):
        label_dir = DATASET / split / "labels"

        counts = Counter()
        widths = {"Car": [], "Vacant": []}
        heights = {"Car": [], "Vacant": []}
        invalid = 0

        for label_file in label_dir.glob("*.txt"):
            for line in label_file.read_text().splitlines():
                fields = line.split()

                if len(fields) != 5:
                    invalid += 1
                    continue

                try:
                    class_id = int(fields[0])
                    x, y, w, h = map(float, fields[1:])
                except ValueError:
                    invalid += 1
                    continue

                if (
                    class_id not in (0, 1)
                    or not (0 <= x <= 1)
                    or not (0 <= y <= 1)
                    or not (0 < w <= 1)
                    or not (0 < h <= 1)
                    or x - w / 2 < 0
                    or x + w / 2 > 1
                    or y - h / 2 < 0
                    or y + h / 2 > 1
                ):
                    invalid += 1
                    continue

                label = "Car" if class_id == 0 else "Vacant"

                counts[label] += 1
                widths[label].append(w)
                heights[label].append(h)

        print(f"\n{split.upper()}")
        print(f"Valid Car boxes: {counts['Car']}")
        print(f"Valid Vacant boxes: {counts['Vacant']}")
        print(f"Invalid annotations: {invalid}")

        for label in ("Car", "Vacant"):
            if widths[label]:
                print(
                    f"{label}: "
                    f"median width={median(widths[label]):.3f}, "
                    f"median height={median(heights[label]):.3f}"
                )

if __name__ == "__main__":
    main()
