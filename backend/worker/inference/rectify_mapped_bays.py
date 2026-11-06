
import json
import math
from pathlib import Path

import cv2
import numpy as np

ROOT = Path("datasets")
OUTPUT = ROOT / "rectified-bays"
TARGET_WIDTH = 160
TARGET_HEIGHT = 256

DATASETS = [
    ("mapping-tests", "vacant", "pexels-giantasparagus-9599927.jpg"),
    ("occupied-tests", "occupied", "pexels-frentescuphotography-15022471.jpg"),
]


def order_points(points):
    """Return four corners ordered clockwise, starting at top-left."""
    points = np.asarray(points, dtype=np.float32)

    if points.shape != (4, 2):
        raise ValueError(f"Expected four 2D points, got {points.shape}")

    center = points.mean(axis=0)
    angles = np.arctan2(
        points[:, 1] - center[1],
        points[:, 0] - center[0],
    )
    points = points[np.argsort(angles)]

    start = np.argmin(points.sum(axis=1))
    return np.roll(points, -start, axis=0)


def extract_points(bay):
    """Support either a list of points or an object containing points."""
    points = bay.get("points", bay.get("polygon"))

    if points is None:
        raise ValueError(f"Missing polygon in bay: {bay}")

    if isinstance(points[0], dict):
        points = [[p["x"], p["y"]] for p in points]

    return order_points(points)


def rectify(image, points):
    destination = np.array(
        [
            [0, 0],
            [TARGET_WIDTH - 1, 0],
            [TARGET_WIDTH - 1, TARGET_HEIGHT - 1],
            [0, TARGET_HEIGHT - 1],
        ],
        dtype=np.float32,
    )

    transform = cv2.getPerspectiveTransform(points, destination)

    return cv2.warpPerspective(
        image,
        transform,
        (TARGET_WIDTH, TARGET_HEIGHT),
    )


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    tiles = []

    for folder, label, image_name in DATASETS:
        directory = ROOT / folder
        image_path = directory / image_name
        mapping_path = directory / "parksight-bay-mapping.json"

        image = cv2.imread(str(image_path))
        if image is None:
            raise FileNotFoundError(image_path)

        mapping = json.loads(mapping_path.read_text())

        if isinstance(mapping, list):
            bays = mapping
        else:
            bays = mapping.get("bays", [])

        print(f"{folder}: {len(bays)} mapped bays")

        for index, bay in enumerate(bays):
            points = extract_points(bay)
            crop = rectify(image, points)

            bay_id = bay.get("id", f"{index + 1:02d}")
            filename = f"{folder}_{bay_id}.jpg"

            cv2.imwrite(str(OUTPUT / filename), crop)

            tiles.append((label, bay_id, crop))

    columns = 6
    tile_width = TARGET_WIDTH
    tile_height = TARGET_HEIGHT + 30
    rows = math.ceil(len(tiles) / columns)

    sheet = np.full(
        (rows * tile_height, columns * tile_width, 3),
        245,
        dtype=np.uint8,
    )

    for index, (label, bay_id, crop) in enumerate(tiles):
        row, col = divmod(index, columns)
        x = col * tile_width
        y = row * tile_height

        sheet[y:y + TARGET_HEIGHT, x:x + TARGET_WIDTH] = crop

        color = (0, 120, 0) if label == "vacant" else (0, 0, 180)

        cv2.putText(
            sheet,
            f"{bay_id} {label}",
            (x + 5, y + TARGET_HEIGHT + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.43,
            color,
            1,
            cv2.LINE_AA,
        )

    output_path = OUTPUT / "rectified_contact_sheet.jpg"
    cv2.imwrite(str(output_path), sheet)

    print(f"Total crops: {len(tiles)}")
    print(f"Contact sheet: {output_path}")


if __name__ == "__main__":
    main()
