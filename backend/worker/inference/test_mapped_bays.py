
import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


BASE = Path(__file__).resolve().parents[2]

DATA_DIR = BASE / "datasets" / "occupied-tests"
IMAGE_PATH = DATA_DIR / "pexels-frentescuphotography-15022471.jpg"
MAPPING_PATH = DATA_DIR / "parksight-bay-mapping.json"
MODEL_PATH = BASE / "runs" / "parking" / "yolo11m_baseline" / "weights" / "best.pt"

OUTPUT_DIR = DATA_DIR / "results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CONF_THRESHOLD = 0.35
MARGIN = 0.08


def classify(detections):
    car = max(
        (score for label, score in detections if label == "Car"),
        default=0.0,
    )
    vacant = max(
        (score for label, score in detections if label == "Vacant"),
        default=0.0,
    )

    if car >= CONF_THRESHOLD and car > vacant + MARGIN:
        return "occupied", car

    if vacant >= CONF_THRESHOLD and vacant > car + MARGIN:
        return "vacant", vacant

    return "unknown", max(car, vacant)


def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

    image = cv2.imread(str(IMAGE_PATH))
    if image is None:
        raise RuntimeError(f"Cannot read image: {IMAGE_PATH}")

    mapping = json.loads(MAPPING_PATH.read_text())

    height, width = image.shape[:2]

    if (
        mapping["image_width"] != width
        or mapping["image_height"] != height
    ):
        raise ValueError(
            "Mapping dimensions do not match reference image"
        )

    model = YOLO(str(MODEL_PATH))
    results = []

    for bay in mapping["bays"]:
        polygon = np.array(
            [[p["x"], p["y"]] for p in bay["points"]],
            dtype=np.int32,
        )

        x, y, w, h = cv2.boundingRect(polygon)

        # Extract the polygon's bounding rectangle.
        crop = image[y:y+h, x:x+w].copy()

        # Mask everything outside the mapped bay.
        local_polygon = polygon - np.array([x, y])
        mask = np.zeros((h, w), dtype=np.uint8)

        cv2.fillPoly(mask, [local_polygon], 255)
        crop = cv2.bitwise_and(crop, crop, mask=mask)

        prediction = model.predict(
            crop,
            imgsz=640,
            conf=0.15,
            verbose=False,
        )[0]

        detections = []

        for box in prediction.boxes:
            class_id = int(box.cls.item())
            label = model.names[class_id]
            confidence = float(box.conf.item())

            if label in {"Car", "Vacant"}:
                detections.append((label, confidence))

        status, confidence = classify(detections)

        cv2.imwrite(
            str(OUTPUT_DIR / f"{bay['id']}_{status}.jpg"),
            crop,
        )

        result = {
            "bay_id": bay["id"],
            "status": status,
            "confidence": round(confidence, 3),
            "detections": [
                {
                    "class": label,
                    "confidence": round(score, 3),
                }
                for label, score in detections
            ],
        }

        results.append(result)

        print(
            f"{bay['id']}: {status.upper():8} "
            f"confidence={confidence:.3f} "
            f"detections={detections}"
        )

    output_path = OUTPUT_DIR / "occupancy_results.json"
    output_path.write_text(json.dumps(results, indent=2))

    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
