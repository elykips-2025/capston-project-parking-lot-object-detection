
from pathlib import Path

import cv2


VIDEO_PATH = (
    Path(__file__).resolve().parents[2]
    / "storage"
    / "videos"
    / "424b3b3c-2c4f-4450-8a6d-8c4e60452425.mp4"
)


def inspect_video():
    if not VIDEO_PATH.is_file():
        raise FileNotFoundError(VIDEO_PATH)

    capture = cv2.VideoCapture(str(VIDEO_PATH))

    try:
        if not capture.isOpened():
            raise RuntimeError("OpenCV could not open the video")

        fps = capture.get(cv2.CAP_PROP_FPS)
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if fps <= 0 or frame_count <= 0:
            raise RuntimeError("Invalid video metadata")

        success, frame = capture.read()

        if not success or frame is None:
            raise RuntimeError("Could not decode the first frame")

        print(f"Resolution: {width}x{height}")
        print(f"Frame rate: {fps:.2f} FPS")
        print(f"Total frames: {frame_count}")
        print(f"Duration: {frame_count / fps:.2f} seconds")
        print(f"First frame decoded: {success}")
        print(f"Frame shape: {frame.shape}")

    finally:
        capture.release()


if __name__ == "__main__":
    inspect_video()
