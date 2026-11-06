
from dataclasses import dataclass
from enum import Enum
import math


class OccupancyState(str, Enum):
    EMPTY = "empty"
    OCCUPIED = "occupied"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class OccupancyDecision:
    state: OccupancyState
    occupied_probability: float
    available: bool


def decide_occupancy(
    occupied_probability: float,
    empty_threshold: float = 0.10,
    occupied_threshold: float = 0.90,
) -> OccupancyDecision:
    if not math.isfinite(occupied_probability):
        raise ValueError("Probability must be finite")

    if not 0.0 <= occupied_probability <= 1.0:
        raise ValueError("Probability must be between 0 and 1")

    if not 0.0 <= empty_threshold < occupied_threshold <= 1.0:
        raise ValueError("Invalid occupancy thresholds")

    if occupied_probability <= empty_threshold:
        state = OccupancyState.EMPTY
    elif occupied_probability >= occupied_threshold:
        state = OccupancyState.OCCUPIED
    else:
        state = OccupancyState.UNKNOWN

    return OccupancyDecision(
        state=state,
        occupied_probability=occupied_probability,
        available=state == OccupancyState.EMPTY,
    )
