
from pathlib import Path

import cv2
import numpy as np

from worker.inference.process_parking_frame import load_bays
from worker.inference.rectify_mapped_bays import extract_points, rectify

BASE = Path("datasets/video-mapping")
IMAGE = BASE / "reference-frame.jpg"
MAPPING = BASE / "parksight-bay-mapping.json"
OUTPUT = BASE / "unknown-bays-contact-sheet.jpg"

UNKNOWN = {
    "A10": ("occupied", 0.302484),
    "A11": ("occupied", 0.276993),
    "A16": ("occupied", 0.572074),
    "A17": ("occupied", 0.324410),
    "A20": ("empty", 0.631676),
    "A22": ("empty", 0.311734),
    "A27": ("empty", 0.405420),
}


def main():
    frame = cv2.imread(str(IMAGE))
    if frame is None:
        raise FileNotFoundError(IMAGE)

    bays = {
        bay["id"]: bay
        for bay in load_bays(MAPPING)
    }

    tile_w = 160
    crop_h = 256
    label_h = 55
    columns = 4
    rows = 2

    sheet = np.full(
        (rows * (crop_h + label_h), columns * tile_w, 3),
        245,
        dtype=np.uint8,
    )

    for index, (bay_id, (actual, probability)) in enumerate(
        UNKNOWN.items()
    ):
        if bay_id not in bays:
            raise ValueError(f"Missing bay: {bay_id}")

        crop = rectify(
            frame,
            extract_points(bays[bay_id]),
        )

        row, col = divmod(index, columns)
        x = col * tile_w
        y = row * (crop_h + label_h)

        sheet[y:y + crop_h, x:x + tile_w] = crop

        cv2.putText(
            sheet,
            f"{bay_id} | {actual}",
            (x + 5, y + crop_h + 19),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.43,
            (20, 20, 20),
            1,
            cv2.LINE_AA,
        )

        cv2.putText(
            sheet,
            f"P(occupied): {probability:.3f}",
            (x + 5, y + crop_h + 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.39,
            (20, 20, 20),
            1,
            cv2.LINE_AA,
        )

    if not cv2.imwrite(str(OUTPUT), sheet):
        raise RuntimeError(f"Failed to save {OUTPUT}")

    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()
