
from pathlib import Path
import cv2
import numpy as np

ROOT = Path("datasets/pklot/sample")
OUTPUT = Path("datasets/pklot/pklot_contact_sheet.jpg")

CAMERAS = ["PUC", "UFPR04", "UFPR05"]
LABELS = ["Empty", "Occupied"]

WIDTH = 160
HEIGHT = 160
HEADER = 26
SAMPLES_PER_GROUP = 5


def main():
    rows = []

    for camera in CAMERAS:
        for label in LABELS:
            images = sorted(
                p for p in (ROOT / camera).rglob("*.jpg")
                if label in p.parts
            )[:SAMPLES_PER_GROUP]

            if len(images) < SAMPLES_PER_GROUP:
                print(
                    f"Warning: {camera}/{label} has "
                    f"only {len(images)} images"
                )

            rows.append((camera, label, images))

    sheet = np.full(
        (
            len(rows) * (HEIGHT + HEADER),
            SAMPLES_PER_GROUP * WIDTH,
            3,
        ),
        245,
        dtype=np.uint8,
    )

    for row_index, (camera, label, images) in enumerate(rows):
        y = row_index * (HEIGHT + HEADER)

        cv2.putText(
            sheet,
            f"{camera} - {label}",
            (8, y + 19),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (30, 30, 30),
            1,
            cv2.LINE_AA,
        )

        for column, path in enumerate(images):
            image = cv2.imread(str(path))

            if image is None:
                print(f"Unreadable: {path}")
                continue

            # Preserve aspect ratio; pad rather than stretch.
            h, w = image.shape[:2]
            scale = min(WIDTH / w, HEIGHT / h)
            resized = cv2.resize(
                image,
                (max(1, int(w * scale)), max(1, int(h * scale))),
            )

            tile = np.full(
                (HEIGHT, WIDTH, 3),
                225,
                dtype=np.uint8,
            )

            rh, rw = resized.shape[:2]
            top = (HEIGHT - rh) // 2
            left = (WIDTH - rw) // 2
            tile[top:top + rh, left:left + rw] = resized

            x = column * WIDTH
            sheet[
                y + HEADER:y + HEADER + HEIGHT,
                x:x + WIDTH,
            ] = tile

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    if not cv2.imwrite(str(OUTPUT), sheet):
        raise RuntimeError("Could not save contact sheet")

    print(f"Saved: {OUTPUT}")
    print("Displayed up to 30 images across six camera/label groups")


if __name__ == "__main__":
    main()
