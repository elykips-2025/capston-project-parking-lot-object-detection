
import cv2
import numpy as np


class FrameAligner:
    def __init__(self, reference_frame):
        if reference_frame is None:
            raise ValueError("Reference frame is required")

        self.reference = reference_frame
        self.orb = cv2.ORB_create(nfeatures=3000)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING)

        gray = cv2.cvtColor(reference_frame, cv2.COLOR_BGR2GRAY)
        self.ref_keypoints, self.ref_descriptors = (
            self.orb.detectAndCompute(gray, None)
        )

        if self.ref_descriptors is None:
            raise RuntimeError("No reference features detected")

    def align(self, frame):
        if frame is None:
            raise ValueError("Input frame is required")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        keypoints, descriptors = self.orb.detectAndCompute(
            gray, None
        )

        if descriptors is None:
            return None

        pairs = self.matcher.knnMatch(
            descriptors, self.ref_descriptors, k=2
        )

        good = [
            m for pair in pairs
            if len(pair) == 2
            for m, n in [pair]
            if m.distance < 0.75 * n.distance
        ]

        if len(good) < 20:
            return None

        source = np.float32([
            keypoints[m.queryIdx].pt for m in good
        ]).reshape(-1, 1, 2)

        destination = np.float32([
            self.ref_keypoints[m.trainIdx].pt for m in good
        ]).reshape(-1, 1, 2)

        H, mask = cv2.findHomography(
            source, destination, cv2.RANSAC, 3.0
        )

        if H is None or mask is None:
            return None

        inliers = mask.ravel().astype(bool)
        count = int(inliers.sum())
        ratio = count / len(good)

        if count < 15 or ratio < 0.45:
            return None

        projected = cv2.perspectiveTransform(
            source[inliers].reshape(-1, 1, 2), H
        )

        errors = np.linalg.norm(
            projected.reshape(-1, 2)
            - destination[inliers].reshape(-1, 2),
            axis=1,
        )

        if not np.isfinite(H).all():
            return None

        if float(np.median(errors)) > 3.0:
            return None

        height, width = self.reference.shape[:2]

        return cv2.warpPerspective(
            frame, H, (width, height)
        )
