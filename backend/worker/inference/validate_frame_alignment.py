
from pathlib import Path

import cv2
import numpy as np

BASE = Path("datasets/video-mapping")
REFERENCE = BASE / "reference-frame.jpg"
VIDEO = Path(
    "storage/videos/424b3b3c-2c4f-4450-8a6d-8c4e60452425.mp4"
)
OUTPUT = BASE / "alignment-diagnostic"

TIMESTAMPS = [0, 5, 10, 15, 20, 25]
MIN_MATCHES = 20
MIN_INLIERS = 15
MIN_INLIER_RATIO = 0.45
MAX_REPROJECTION_ERROR = 3.0


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    reference = cv2.imread(str(REFERENCE))
    if reference is None:
        raise FileNotFoundError(REFERENCE)

    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {VIDEO}")

    orb = cv2.ORB_create(nfeatures=3000)

    ref_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
    ref_keypoints, ref_descriptors = orb.detectAndCompute(
        ref_gray, None
    )

    if ref_descriptors is None:
        raise RuntimeError("No reference features detected")

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)

    print(
        f"{'Time':<8} {'Matches':<9} {'Inliers':<9} "
        f"{'Ratio':<9} {'Error':<9} {'Status'}"
    )

    try:
        for seconds in TIMESTAMPS:
            cap.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
            ok, frame = cap.read()

            if not ok:
                print(f"{seconds:<8} Frame unavailable")
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            keypoints, descriptors = orb.detectAndCompute(
                gray, None
            )

            if descriptors is None:
                print(f"{seconds:<8} FAIL: no features")
                continue

            pairs = matcher.knnMatch(
                descriptors, ref_descriptors, k=2
            )

            good = [
                m for pair in pairs
                if len(pair) == 2
                for m, n in [pair]
                if m.distance < 0.75 * n.distance
            ]

            if len(good) < MIN_MATCHES:
                print(
                    f"{seconds:<8} FAIL: insufficient matches "
                    f"({len(good)})"
                )
                continue

            source = np.float32([
                keypoints[m.queryIdx].pt for m in good
            ]).reshape(-1, 1, 2)

            destination = np.float32([
                ref_keypoints[m.trainIdx].pt for m in good
            ]).reshape(-1, 1, 2)

            H, mask = cv2.findHomography(
                source,
                destination,
                cv2.RANSAC,
                MAX_REPROJECTION_ERROR,
            )

            if H is None or mask is None:
                print(f"{seconds:<8} FAIL: homography")
                continue

            inliers = mask.ravel().astype(bool)
            count = int(inliers.sum())
            ratio = count / len(good)

            projected = cv2.perspectiveTransform(
                source[inliers].reshape(-1, 1, 2), H
            )
            errors = np.linalg.norm(
                projected.reshape(-1, 2)
                - destination[inliers].reshape(-1, 2),
                axis=1,
            )
            median_error = float(np.median(errors))

            valid = (
                count >= MIN_INLIERS
                and ratio >= MIN_INLIER_RATIO
                and median_error <= MAX_REPROJECTION_ERROR
                and np.isfinite(H).all()
            )

            status = "PASS" if valid else "FAIL"

            print(
                f"{seconds:<8} {len(good):<9} {count:<9} "
                f"{ratio:<9.2f} {median_error:<9.2f} {status}"
            )

            if not valid:
                continue

            height, width = reference.shape[:2]
            aligned = cv2.warpPerspective(
                frame, H, (width, height)
            )

            # Blend aligned frame with reference to reveal
            # registration errors and vehicle movement.
            comparison = cv2.addWeighted(
                reference, 0.5, aligned, 0.5, 0
            )

            cv2.imwrite(
                str(OUTPUT / f"aligned-{seconds:02d}s.jpg"),
                aligned,
            )
            cv2.imwrite(
                str(OUTPUT / f"comparison-{seconds:02d}s.jpg"),
                comparison,
            )
    finally:
        cap.release()


if __name__ == "__main__":
    main()
