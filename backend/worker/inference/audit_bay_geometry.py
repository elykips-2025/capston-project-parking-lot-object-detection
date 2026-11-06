
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path("datasets")

DATASETS = [
    ("mapping-tests", "vacant"),
    ("occupied-tests", "occupied"),
]

MIN_AREA = 100
MAX_EDGE_RATIO = 8.0
MAX_OPPOSITE_RATIO = 4.0


def get_points(bay):
    points = bay.get("points", bay.get("polygon"))

    if points is None:
        raise ValueError("Missing polygon")

    if isinstance(points[0], dict):
        points = [[p["x"], p["y"]] for p in points]

    points = np.asarray(points, dtype=np.float32)

    if points.shape != (4, 2):
        raise ValueError(f"Expected 4 corners, got {points.shape}")

    if not np.isfinite(points).all():
        raise ValueError("Non-finite coordinates")

    return points


def audit(points):
    issues = []

    hull = cv2.convexHull(points)
    hull_area = cv2.contourArea(hull)
    polygon_area = cv2.contourArea(points)

    if len(hull) != 4:
        issues.append("non-convex or duplicate corners")

    if polygon_area < MIN_AREA:
        issues.append("very small polygon")

    if hull_area > 0 and polygon_area / hull_area < 0.95:
        issues.append("possible crossed or unordered corners")

    edges = np.linalg.norm(
        np.roll(points, -1, axis=0) - points,
        axis=1,
    )

    if edges.min() < 1:
        issues.append("degenerate edge")
        edge_ratio = float("inf")
    else:
        edge_ratio = float(edges.max() / edges.min())

    if edge_ratio > MAX_EDGE_RATIO:
        issues.append("extreme edge-length ratio")

    opposite_ratios = [
        max(edges[0], edges[2]) / max(min(edges[0], edges[2]), 1e-6),
        max(edges[1], edges[3]) / max(min(edges[1], edges[3]), 1e-6),
    ]

    if max(opposite_ratios) > MAX_OPPOSITE_RATIO:
        issues.append("extreme perspective taper")

    return {
        "area": round(float(polygon_area), 1),
        "edge_ratio": round(edge_ratio, 2),
        "max_opposite_ratio": round(max(opposite_ratios), 2),
        "issues": issues,
    }


def main():
    total = 0
    flagged = 0

    for folder, label in DATASETS:
        path = ROOT / folder / "parksight-bay-mapping.json"
        mapping = json.loads(path.read_text())
        bays = mapping if isinstance(mapping, list) else mapping["bays"]

        print(f"\n{folder.upper()} ({label})")

        for index, bay in enumerate(bays):
            bay_id = bay.get("id", f"A{index + 1:02d}")
            total += 1

            try:
                result = audit(get_points(bay))
                issues = result["issues"]

                if issues:
                    flagged += 1

                status = "FLAG" if issues else "PASS"

                print(
                    f"{bay_id}: {status} "
                    f"area={result['area']} "
                    f"edge_ratio={result['edge_ratio']} "
                    f"taper={result['max_opposite_ratio']} "
                    f"issues={issues}"
                )

            except (ValueError, KeyError, IndexError) as exc:
                flagged += 1
                print(f"{bay_id}: ERROR {exc}")

    print(f"\nTOTAL: {total}")
    print(f"PASSED: {total - flagged}")
    print(f"FLAGGED: {flagged}")


if __name__ == "__main__":
    main()
