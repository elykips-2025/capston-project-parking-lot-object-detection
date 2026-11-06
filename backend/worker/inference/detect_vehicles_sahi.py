
from pathlib import Path
from time import perf_counter

import cv2
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction


BACKEND_DIR = Path(__file__).resolve().parents[2]

VIDEO_PATH = (
    BACKEND_DIR
    / "storage"
    / "videos"
    / "424b3b3c-2c4f-4450-8a6d-8c4e60452425.mp4"
)

MODEL_PATH = BACKEND_DIR / "yolo11n.pt"

OUTPUT_PATH = (
    BACKEND_DIR
    / "storage"
    / "yolo_sahi_preview.jpg"
)

VEHICLE_CLASSES = {
    "car",
    "motorcycle",
    "bus",
    "truck",
}


def detect_vehicles():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(MODEL_PATH)

    model = AutoDetectionModel.from_pretrained(
        model_type="ultralytics",
        model_path=str(MODEL_PATH),
        confidence_threshold=0.20,
        device="cpu",
    )

    capture = cv2.VideoCapture(str(VIDEO_PATH))

    try:
        if not capture.isOpened():
            raise RuntimeError("Unable to open video")

        success, frame = capture.read()

        if not success:
            raise RuntimeError("Unable to decode first frame")

        start = perf_counter()

        result = get_sliced_prediction(
            image=frame,
            detection_model=model,
            slice_height=320,
            slice_width=320,
            overlap_height_ratio=0.20,
            overlap_width_ratio=0.20,
            perform_standard_pred=False,
            postprocess_type="NMS",
            postprocess_match_threshold=0.5,
            verbose=0,
        )

        elapsed = perf_counter() - start

        detections = [
            prediction
            for prediction in result.object_prediction_list
            if prediction.category.name in VEHICLE_CLASSES
        ]

        annotated = frame.copy()

        for detection in detections:
            bbox = detection.bbox

            x1 = int(bbox.minx)
            y1 = int(bbox.miny)
            x2 = int(bbox.maxx)
            y2 = int(bbox.maxy)

            confidence = float(detection.score.value)
            label = detection.category.name

            cv2.rectangle(
                annotated,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2,
            )

            cv2.putText(
                annotated,
                f"{label} {confidence:.2f}",
                (x1, max(15, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (0, 255, 0),
                1,
            )

        OUTPUT_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not cv2.imwrite(str(OUTPUT_PATH), annotated):
            raise RuntimeError("Failed to save preview")

        print(f"Vehicles detected: {len(detections)}")
        print(f"Inference time: {elapsed:.2f} seconds")
        print(f"Preview saved to: {OUTPUT_PATH}")

    finally:
        capture.release()


if __name__ == "__main__":
    detect_vehicles()
