
from pathlib import Path
import csv

from ultralytics import YOLO

BACKEND = Path(__file__).resolve().parents[2]
DATASET = BACKEND / "datasets" / "parksight_4k_10bay_poc"
MODEL = BACKEND / "runs/parking/yolo11m_baseline/weights/best.pt"

def main():
    if not DATASET.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET}")

    if not MODEL.exists():
        raise FileNotFoundError(f"Model not found: {MODEL}")

    
    images = sorted(
        p for p in DATASET.iterdir()
        if p.is_file()
        and p.suffix.lower() == ".png"
        and (
            p.name.startswith("O")
            or p.name.startswith("V")
        )
    )


    if not images:
        raise RuntimeError(
            "No crop images found. Check the dataset directory structure."
        )

    model = YOLO(str(MODEL))

    print(f"Found {len(images)} candidate crop images")

    for image in images:
        result = model.predict(
            source=str(image),
            imgsz=640,
            conf=0.25,
            verbose=False,
            save=True,
        )[0]

        detections = []

        
        for box in result.boxes:
            class_id = int(box.cls.item())
            confidence = float(box.conf.item())
            class_name = model.names[class_id]

            coordinates = [
                round(float(value), 1)
                for value in box.xyxy[0].tolist()
            ]

            detections.append(
                {
                    "class": class_name,
                    "confidence": round(confidence, 3),
                    "bbox": coordinates,
                }
            )


        print(f"{image.name}: {detections or 'No detections'}")


if __name__ == "__main__":
    main()
