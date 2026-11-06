
from pathlib import Path
import cv2
import numpy as np

ROOT = Path("datasets/parking-vehicles")
OUTPUT = Path("datasets/candidate-crops")

IMAGE_NAME = (
    "4k-time-lapse-car-parking-lot-stock-video-download-video-"
    "clip-now-istock_TyROSAGZ_mp4-263_jpg."
    "rf.a23e9cecdae9b2f5f4edbccafa581ed7.jpg"
)

def main():
    image_path = ROOT / "train" / "images" / IMAGE_NAME
    label_path = (
        ROOT / "train" / "labels" /
        f"{image_path.stem}.txt"
    )

    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(image_path)

    if not label_path.exists():
        raise FileNotFoundError(label_path)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    height, width = image.shape[:2]
    samples = []

    for line in label_path.read_text().splitlines():
        fields = line.split()
        class_id = int(fields[0])
        values = list(map(float, fields[1:]))

        if class_id not in (0, 1):
            continue

        if len(values) == 4:
            x, y, w, h = values
            x1 = (x - w / 2) * width
            y1 = (y - h / 2) * height
            x2 = (x + w / 2) * width
            y2 = (y + h / 2) * height
        else:
            points = np.array(values).reshape(-1, 2)
            points[:, 0] *= width
            points[:, 1] *= height

            x1, y1 = points.min(axis=0)
            x2, y2 = points.max(axis=0)

        box_width = x2 - x1
        box_height = y2 - y1

        # Add 15% context around each annotation.
        margin_x = box_width * 0.15
        margin_y = box_height * 0.15

        left = max(0, int(x1 - margin_x))
        top = max(0, int(y1 - margin_y))
        right = min(width, int(np.ceil(x2 + margin_x)))
        bottom = min(height, int(np.ceil(y2 + margin_y)))

        if right <= left or bottom <= top:
            continue

        crop = image[top:bottom, left:right]
        crop = cv2.resize(crop, (224, 224))

        label = "Occupied" if class_id == 0 else "Vacant"
        samples.append((label, crop))

    # Keep a balanced visual sample.
    occupied = [s for s in samples if s[0] == "Occupied"][:12]
    vacant = [s for s in samples if s[0] == "Vacant"][:12]

    selected = occupied + vacant

    if not selected:
        raise RuntimeError("No valid crops found")

    tile_width = 224
    tile_height = 254
    columns = 4
    rows = (len(selected) + columns - 1) // columns

    sheet = np.full(
        (rows * tile_height, columns * tile_width, 3),
        245,
        dtype=np.uint8,
    )

    for index, (label, crop) in enumerate(selected):
        row, col = divmod(index, columns)

        x = col * tile_width
        y = row * tile_height

        sheet[y:y+224, x:x+224] = crop

        color = (0, 0, 180) if label == "Occupied" else (0, 130, 0)

        cv2.putText(
            sheet,
            label,
            (x + 8, y + 244),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
        )

    output_path = OUTPUT / "candidate_contact_sheet.jpg"
    cv2.imwrite(str(output_path), sheet)

    print(f"Source image: {image_path.name}")
    print(f"Total candidate annotations: {len(samples)}")
    print(f"Occupied samples displayed: {len(occupied)}")
    print(f"Vacant samples displayed: {len(vacant)}")
    print(f"Saved: {output_path}")

if __name__ == "__main__":
    main()
