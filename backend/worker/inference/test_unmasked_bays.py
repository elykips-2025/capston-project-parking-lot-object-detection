
import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

BASE = Path(__file__).resolve().parents[2]
MODEL_PATH = BASE / "runs/parking/yolo11m_baseline/weights/best.pt"

DATASETS = {
    "mapping-tests": "pexels-giantasparagus-9599927.jpg",
    "occupied-tests": "pexels-frentescuphotography-15022471.jpg",
}

CONF_THRESHOLD = 0.35
MARGIN = 0.08
CONTEXT = 0.15


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


def evaluate_dataset(model, dataset_name, filename):
    directory = BASE / "datasets" / dataset_name
    image = cv2.imread(str(directory / filename))

    if image is None:
        raise RuntimeError(f"Cannot read image: {filename}")

    mapping = json.loads(
        (directory / "parksight-bay-mapping.json").read_text()
    )

    image_height, image_width = image.shape[:2]

    if (
        mapping["image_width"] != image_width
        or mapping["image_height"] != image_height
    ):
        raise ValueError(f"Image dimensions mismatch: {dataset_name}")

    results = []

    for bay in mapping["bays"]:
        polygon = np.array(
            [[p["x"], p["y"]] for p in bay["points"]],
            dtype=np.int32,
        )

        x, y, w, h = cv2.boundingRect(polygon)

        pad_x = round(w * CONTEXT)
        pad_y = round(h * CONTEXT)

        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(image_width, x + w + pad_x)
        y2 = min(image_height, y + h + pad_y)

        crop = image[y1:y2, x1:x2]

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

            if label not in {"Car", "Vacant"}:
                continue

            bx1, by1, bx2, by2 = box.xyxy[0].tolist()

            center_x = (bx1 + bx2) / 2 + x1
            center_y = (by1 + by2) / 2 + y1

            inside = cv2.pointPolygonTest(
                polygon.astype(np.float32),
                (center_x, center_y),
                False,
            )

            if inside < 0:
                continue

            detections.append(
                (label, float(box.conf.item()))
            )

        status, confidence = classify(detections)

        results.append({
            "bay_id": bay["id"],
            "status": status,
            "confidence": round(confidence, 3),
        })

        print(
            f"{bay['id']}: {status.upper():8} "
            f"confidence={confidence:.3f}"
        )

    output = directory / "results" / "occupancy_unmasked.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2))

    return results


def main():
    model = YOLO(str(MODEL_PATH))

    confusion = {
        "occupied": {"occupied": 0, "vacant": 0, "unknown": 0},
        "vacant": {"occupied": 0, "vacant": 0, "unknown": 0},
    }

    for dataset_name, filename in DATASETS.items():
        actual = (
            "vacant"
            if dataset_name == "mapping-tests"
            else "occupied"
        )

        print(f"\n{dataset_name.upper()}")

        results = evaluate_dataset(
            model, dataset_name, filename
        )

        for result in results:
            confusion[actual][result["status"]] += 1

    total = sum(sum(row.values()) for row in confusion.values())
    correct = (
        confusion["occupied"]["occupied"]
        + confusion["vacant"]["vacant"]
    )
    classified = total - sum(
        row["unknown"] for row in confusion.values()
    )
    false_vacant = confusion["occupied"]["vacant"]

    print("\nCONFUSION MATRIX")
    print(f"{'Actual':12} {'Occupied':>10} {'Vacant':>10} {'Unknown':>10}")

    for actual, row in confusion.items():
        print(
            f"{actual:12} "
            f"{row['occupied']:>10} "
            f"{row['vacant']:>10} "
            f"{row['unknown']:>10}"
        )

    print("\nMETRICS")
    print(f"Total bays: {total}")
    print(f"Correct: {correct}")
    print(f"Coverage: {classified / total:.1%}")
    print(f"Overall accuracy: {correct / total:.1%}")
    print(
        "Accuracy on classified bays: "
        f"{correct / classified:.1%}"
        if classified else "No classified bays"
    )
    print(f"False-vacant predictions: {false_vacant}")


if __name__ == "__main__":
    main()
