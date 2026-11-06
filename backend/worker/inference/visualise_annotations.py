
from pathlib import Path
import random

import cv2
import numpy as np

DATASET = Path("datasets/parking-vehicles")
OUTPUT = Path("datasets/annotation-audit")
SPLIT = "train"
SAMPLE_COUNT = 10

COLORS = {
    0: (0, 0, 255),  # Car: red (OpenCV BGR)
    1: (0, 255, 0),  # Vacant: green
}

def main():
    image_dir = DATASET / SPLIT / "images"
    label_dir = DATASET / SPLIT / "labels"

    OUTPUT.mkdir(parents=True, exist_ok=True)

    candidates = []

    for label_path in sorted(label_dir.glob("*.txt")):
        lines = [
            line.split()
            for line in label_path.read_text().splitlines()
            if line.strip()
        ]

        classes = {int(fields[0]) for fields in lines}

        # Select images containing both Car and Vacant.
        if classes != {0, 1}:
            continue

        image_path = next(
            (
                image_dir / f"{label_path.stem}{ext}"
                for ext in (".jpg", ".jpeg", ".png")
                if (image_dir / f"{label_path.stem}{ext}").exists()
            ),
            None,
        )

        if image_path:
            candidates.append((image_path, lines))

    random.seed(42)
    selected = random.sample(
        candidates,
        min(SAMPLE_COUNT, len(candidates)),
    )

    print(f"Images containing both classes: {len(candidates)}")

    for index, (image_path, lines) in enumerate(selected, 1):
        image = cv2.imread(str(image_path))

        if image is None:
            continue

        height, width = image.shape[:2]

        for fields in lines:
            class_id = int(fields[0])
            values = list(map(float, fields[1:]))
            color = COLORS[class_id]
            label = "Car" if class_id == 0 else "Vacant"

            if len(values) == 4:
                x, y, w, h = values

                x1 = int((x - w / 2) * width)
                y1 = int((y - h / 2) * height)
                x2 = int((x + w / 2) * width)
                y2 = int((y + h / 2) * height)

                cv2.rectangle(
                    image, (x1, y1), (x2, y2), color, 2
                )
                text_position = (x1, max(15, y1 - 4))

            else:
                points = np.array(
                    [
                        [values[i] * width, values[i + 1] * height]
                        for i in range(0, len(values), 2)
                    ],
                    dtype=np.float32,
                ).astype(np.int32)

                cv2.polylines(
                    image, [points], True, color, 2
                )

                x, y = points.min(axis=0)
                text_position = (int(x), max(15, int(y) - 4))

            cv2.putText(
                image,
                label,
                text_position,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                color,
                1,
                cv2.LINE_AA,
            )

        output_path = OUTPUT / f"audit_{index:02d}.jpg"
        cv2.imwrite(str(output_path), image)

        print(f"Saved: {output_path} ({image_path.name})")

    print(f"\nCompleted: {len(selected)} images")

if __name__ == "__main__":
    main()
