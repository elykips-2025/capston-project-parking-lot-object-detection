
from pathlib import Path

import cv2


VIDEO_PATH = (
    Path(__file__).resolve().parents[2]
    / "storage"
    / "videos"
    / "424b3b3c-2c4f-4450-8a6d-8c4e60452425.mp4"
)

TARGET_FPS = 5.0


def iter_sampled_frames(video_path: Path, target_fps: float):
    """Yield (timestamp_seconds, frame_bgr) from a video."""
    if target_fps <= 0:
        raise ValueError("Target FPS must be positive")

    capture = cv2.VideoCapture(str(video_path))

    if not capture.isOpened():
        raise RuntimeError(f"Unable to open video: {video_path}")

    try:
        source_fps = capture.get(cv2.CAP_PROP_FPS)

        if not 0 < source_fps < float("inf"):
            raise RuntimeError("Invalid source frame rate")

        if target_fps > source_fps:
            raise ValueError(
                "Target FPS cannot exceed source FPS"
            )

        frame_index = 0
        next_sample_time = 0.0

        while True:
            success, frame = capture.read()

            if not success:
                break

            timestamp = frame_index / source_fps

            if timestamp + 1e-9 >= next_sample_time:
                yield timestamp, frame
                next_sample_time += 1.0 / target_fps

            frame_index += 1

    finally:
        capture.release()


def sample_frames(video_path: Path, target_fps: float):
    """CLI inspection wrapper, retained for compatibility."""
    count = 0

    for timestamp, frame in iter_sampled_frames(
        video_path, target_fps
    ):
        count += 1
        print(
            f"Sample {count}: "
            f"time={timestamp:.2f}s, "
            f"shape={frame.shape}"
        )

    print(f"\nSampled frames: {count}")
    print(f"Target FPS: {target_fps}")


if __name__ == "__main__":
    sample_frames(VIDEO_PATH, TARGET_FPS)
