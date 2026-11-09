import csv
from pathlib import Path

from worker.inference.frame_alignment import FrameAligner
from worker.inference.sample_frames import iter_sampled_frames
from worker.inference.process_parking_frame import process_frame
from worker.inference.occupancy_classifier import OccupancyClassifier
from worker.inference.temporal_occupancy import TemporalOccupancyEngine


FIELDS = [
    "timestamp_seconds",
    "bay_id",
    "state",
    "occupied_probability",
    "available",
    "temporal_state",
    "temporal_available",
]


def process_video(
    video_path: Path,
    reference,
    bays: list,
    checkpoint_path: Path,
    output_path: Path,
    target_fps: float = 1.0,
):
    """Process recorded CCTV footage using supplied camera configuration."""

    if not bays:
        raise ValueError("At least one parking bay is required")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_output = output_path.with_name(
        output_path.name + ".tmp"
    )

    aligner = FrameAligner(reference)
    classifier = OccupancyClassifier(str(checkpoint_path))
    temporal_engine = TemporalOccupancyEngine()

    expected_bays = len(bays)

    processed = 0
    rejected = 0
    predictions_written = 0

    try:
        with temporary_output.open("w", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=FIELDS,
            )
            writer.writeheader()

            for timestamp, frame in iter_sampled_frames(
                Path(video_path),
                target_fps,
            ):
                aligned = aligner.align(frame)

                if aligned is None:
                    rejected += 1
                    continue

                results = process_frame(
                    aligned,
                    bays,
                    classifier,
                )

                if len(results) != expected_bays:
                    raise RuntimeError(
                        "Incomplete parking-bay predictions"
                    )

                if {result["bay_id"] for result in results} != {
                    bay["id"] for bay in bays
                }:
                    raise RuntimeError(
                        "Unexpected parking-bay predictions"
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

                processed += 1
                predictions_written += len(results)

        if processed == 0:
            raise RuntimeError(
                "No video frames were successfully aligned"
            )

        temporary_output.replace(output_path)

    finally:
        temporary_output.unlink(missing_ok=True)

    return {
        "frames_processed": processed,
        "frames_rejected": rejected,
        "predictions_written": predictions_written,
        "parking_bays": expected_bays,
        "output_path": str(output_path),
    }
