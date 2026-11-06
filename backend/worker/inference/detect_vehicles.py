
from pathlib import Path

import cv2
from ultralytics import YOLO


VIDEO_PATH = (
    Path(__file__).resolve().parents[2]
    / "storage"
    / "videos"
    / "424b3b3c-2c4f-4450-8a6d-8c4e60452425.mp4"
)

MODEL_NAME = "yolo11m.pt"

# COCO vehicle classes
VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


def detect_vehicles():
    model = YOLO(MODEL_NAME)

    capture = cv2.VideoCapture(str(VIDEO_PATH))

    try:
        if not capture.isOpened():
            raise RuntimeError("Unable to open video")

        success, frame = capture.read()

        if not success:
            raise RuntimeError("Unable to decode first frame")

        results = model.predict(
            source=frame,
            imgsz=1280,
            conf=0.20,
            iou=0.45,
            classes=list(VEHICLE_CLASSES),
            verbose=False,
        )

        detections = []

        for box in results[0].boxes:
            class_id = int(box.cls.item())

            detections.append({
                "class": VEHICLE_CLASSES[class_id],
                "confidence": round(
                    float(box.conf.item()), 3
                ),
                "bbox": [
                    round(float(value), 1)
                    for value in box.xyxy[0].tolist()
                ],
            })

        print(f"Vehicles detected: {len(detections)}")

        for detection in detections:
            print(detection)

        # Generate an annotated preview of YOLO detections
        annotated_frame = results[0].plot()

        output_path = (
            Path(__file__).resolve().parents[2]
            / "storage"
            / "yolo_detection_preview.jpg"
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        saved = cv2.imwrite(
            str(output_path),
            annotated_frame,
        )

        if not saved:
            raise RuntimeError(
                f"Failed to save preview: {output_path}"
            )

        print(f"Preview saved to: {output_path}")

    finally:
        capture.release()


if __name__ == "__main__":
    detect_vehicles()
