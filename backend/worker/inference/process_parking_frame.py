
import json
from pathlib import Path

import cv2
from PIL import Image

from worker.inference.occupancy_classifier import OccupancyClassifier
from worker.inference.rectify_mapped_bays import (
    extract_points,
    rectify,
)


def process_frame(frame_bgr, bays, classifier):
    """Classify mapped parking bays in a single video frame."""
    if frame_bgr is None or frame_bgr.size == 0:
        raise ValueError("Invalid video frame")

    results = []
    seen_ids = set()

    for index, bay in enumerate(bays):
        bay_id = str(bay.get("id", f"{index + 1:02d}"))

        if bay_id in seen_ids:
            raise ValueError(f"Duplicate bay ID: {bay_id}")
        seen_ids.add(bay_id)

        points = extract_points(bay)

        height, width = frame_bgr.shape[:2]
        if (
            (points[:, 0] < 0).any()
            or (points[:, 0] >= width).any()
            or (points[:, 1] < 0).any()
            or (points[:, 1] >= height).any()
        ):
            raise ValueError(
                f"Bay {bay_id} has coordinates outside the frame"
            )

        crop_bgr = rectify(frame_bgr, points)
        crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)

        decision = classifier.predict(
            Image.fromarray(crop_rgb)
        )

        results.append({
            "bay_id": bay_id,
            "state": decision.state.value,
            "occupied_probability": round(
                decision.occupied_probability, 6
            ),
            "available": decision.available,
        })

    return results


def load_bays(mapping_path):
    mapping = json.loads(Path(mapping_path).read_text())

    if isinstance(mapping, list):
        bays = mapping
    elif isinstance(mapping, dict):
        bays = mapping.get("bays")
    else:
        raise ValueError("Invalid mapping format")

    if not isinstance(bays, list) or not bays:
        raise ValueError("Mapping must contain at least one bay")

    return bays


if __name__ == "__main__":
    image_path = Path(
        "datasets/occupied-tests/"
        "pexels-frentescuphotography-15022471.jpg"
    )
    mapping_path = Path(
        "datasets/occupied-tests/parksight-bay-mapping.json"
    )

    frame = cv2.imread(str(image_path))
    if frame is None:
        raise FileNotFoundError(image_path)

    classifier = OccupancyClassifier(
        "runs/occupancy/mobilenetv3_pilot/best.pt"
    )

    results = process_frame(
        frame,
        load_bays(mapping_path),
        classifier,
    )

    for result in results:
        print(
            f"{result['bay_id']:<5} "
            f"state={result['state']:<8} "
            f"p_occupied={result['occupied_probability']:.4f} "
            f"available={result['available']}"
        )

    print(f"\nProcessed {len(results)} parking bays")
