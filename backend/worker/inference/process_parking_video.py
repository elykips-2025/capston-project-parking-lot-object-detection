
import csv
from pathlib import Path

import cv2

from worker.inference.frame_alignment import FrameAligner
from worker.inference.sample_frames import iter_sampled_frames
from worker.inference.process_parking_frame import (
    load_bays,
    process_frame,
)
from worker.inference.occupancy_classifier import OccupancyClassifier
from worker.inference.temporal_occupancy import TemporalOccupancyEngine


BASE = Path("datasets/video-mapping")

VIDEO = Path(
    "storage/videos/424b3b3c-2c4f-4450-8a6d-8c4e60452425.mp4"
)
REFERENCE = BASE / "reference-frame.jpg"
MAPPING = BASE / "parksight-bay-mapping.json"
CHECKPOINT = Path(
    "runs/occupancy/mobilenetv3_pilot/best.pt"
)
OUTPUT = BASE / "video-occupancy-results.csv"

TARGET_FPS = 1.0


FIELDS = [
    "timestamp_seconds",
    "bay_id",
    "state",
    "occupied_probability",
    "available",
    "temporal_state",
    "temporal_available",
]



def main():
    reference = cv2.imread(str(REFERENCE))
    if reference is None:
        raise FileNotFoundError(REFERENCE)

    aligner = FrameAligner(reference)
    classifier = OccupancyClassifier(str(CHECKPOINT))
    bays = load_bays(MAPPING)
    temporal_engine = TemporalOccupancyEngine()

    expected_bays = len(bays)

    frames_processed = 0
    frames_rejected = 0
    predictions_written = 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    # Write to a temporary file so failed processing does not
    # leave a partial CSV presented as a completed result.
    temporary_output = OUTPUT.with_suffix(".csv.tmp")

    try:
        with temporary_output.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            writer.writeheader()

            for timestamp, frame in iter_sampled_frames(
                VIDEO, TARGET_FPS
            ):
                aligned = aligner.align(frame)

                if aligned is None:
                    frames_rejected += 1
                    print(
                        f"REJECTED frame at {timestamp:.2f}s: "
                        "alignment failed"
                    )
                    continue

                results = process_frame(
                    aligned,
                    bays,
                    classifier,
                )

                if len(results) != expected_bays:
                    raise RuntimeError(
                        "Incomplete bay predictions"
                    )

                for result in results:
                    temporal = temporal_engine.update(
                        result["bay_id"],
                        result["state"],
                    )

                    writer.writerow({
                        "timestamp_seconds": round(timestamp, 3),
                        **result,
                        "temporal_state": temporal["state"],
                        "temporal_available": temporal["available"],
                    })

                frames_processed += 1
                predictions_written += len(results)

                print(
                    f"Processed {timestamp:.2f}s: "
                    f"{len(results)} bays"
                )

        temporary_output.replace(OUTPUT)

    finally:
        if temporary_output.exists():
            temporary_output.unlink()

    print("\n=== VIDEO PROCESSING SUMMARY ===")
    print(f"Frames processed: {frames_processed}")
    print(f"Frames rejected: {frames_rejected}")
    print(f"Predictions written: {predictions_written}")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
