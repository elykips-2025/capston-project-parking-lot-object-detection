
from pathlib import Path

from ultralytics import YOLO


BACKEND_DIR = Path(__file__).resolve().parents[2]

DATASET_CONFIG = (
    BACKEND_DIR
    / "datasets"
    / "parking-vehicles"
    / "data.yaml"
)

MODEL_PATH = BACKEND_DIR / "yolo11m.pt"

OUTPUT_DIR = BACKEND_DIR / "runs" / "parking"


def main():
    if not DATASET_CONFIG.is_file():
        raise FileNotFoundError(DATASET_CONFIG)

    model = YOLO(str(MODEL_PATH))

    model.train(
        data=str(DATASET_CONFIG),
        epochs=20,
        imgsz=640,
        batch=4,
        device="mps",
        workers=0,
        project=str(OUTPUT_DIR),
        name="yolo11m_baseline",
        exist_ok=False,
        patience=7,
        seed=42,
        plots=True,
    )


if __name__ == "__main__":
    main()
