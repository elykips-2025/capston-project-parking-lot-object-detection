
from pathlib import Path

import cv2

DATASET_DIR = (
    Path(__file__).resolve().parents[2]
    / "datasets"
    / "parking-vehicles"
)

image_dir = DATASET_DIR / "train" / "images"
label_dir = DATASET_DIR / "train" / "labels"

classes = ["Car", "Vacant"]

for image_path in sorted(image_dir.iterdir()):
    if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        continue

    label_path = label_dir / f"{image_path.stem}.txt"

    if not label_path.exists():
        continue

    image = cv2.imread(str(image_path))

    if image is None:
        continue

    height, width = image.shape[:2]

    for line in label_path.read_text().splitlines():
        values = line.split()

        if len(values) != 5:
            continue

        class_id = int(values[0])
        x, y, w, h = map(float, values[1:])

        x1 = int((x - w / 2) * width)
        y1 = int((y - h / 2) * height)
        x2 = int((x + w / 2) * width)
        y2 = int((y + h / 2) * height)

        color = (0, 255, 0) if class_id == 0 else (0, 0, 255)

        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

        cv2.putText(
            image,
            classes[class_id],
            (x1, max(15, y1 - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )

    output_path = DATASET_DIR / "annotation_preview.jpg"

    cv2.imwrite(str(output_path), image)

    print(f"Preview saved: {output_path}")
    break
