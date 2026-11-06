
from pathlib import Path

import cv2
import numpy as np

from worker.inference.occupancy_classifier import OccupancyClassifier
from worker.inference.process_parking_frame import load_bays, process_frame
from worker.inference.rectify_mapped_bays import extract_points

ROOT = Path("datasets/video-mapping")
OUTPUT = ROOT / "occupancy-overlay.jpg"

COLORS = {
    "empty": (0, 200, 0),       # Green (BGR)
    "occupied": (0, 0, 230),    # Red
    "unknown": (0, 190, 255),   # Amber
}


def main():
    frame = cv2.imread(str(ROOT / "reference-frame.jpg"))
    if frame is None:
        raise FileNotFoundError("Reference frame not found")

    bays = load_bays(ROOT / "parksight-bay-mapping.json")

    classifier = OccupancyClassifier(
        "runs/occupancy/mobilenetv3_pilot/best.pt"
    )

    results = process_frame(frame, bays, classifier)
    by_id = {result["bay_id"]: result for result in results}

    overlay = frame.copy()

    for bay in bays:
        result = by_id[str(bay["id"])]
        points = extract_points(bay).astype(np.int32)
        color = COLORS[result["state"]]

        cv2.fillPoly(overlay, [points], color)

    # Keep the original vehicles visible beneath the overlay.
    output = cv2.addWeighted(overlay, 0.25, frame, 0.75, 0)

    for bay in bays:
        result = by_id[str(bay["id"])]
        points = extract_points(bay).astype(np.int32)
        color = COLORS[result["state"]]

        cv2.polylines(output, [points], True, color, 2)

        center = points.mean(axis=0).astype(int)
        label = str(bay["id"])

        cv2.putText(
            output,
            label,
            (int(center[0]) - 13, int(center[1]) + 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.36,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    if not cv2.imwrite(str(OUTPUT), output):
        raise RuntimeError("Failed to save overlay")

    print(f"Processed bays: {len(results)}")
    print(f"Overlay saved: {OUTPUT}")


if __name__ == "__main__":
    main()
