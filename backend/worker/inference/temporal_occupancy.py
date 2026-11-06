
from collections import defaultdict, deque


class TemporalOccupancyEngine:
    """
    Stabilise parking-bay occupancy decisions using
    a rolling window of recent observations.
    """

    def __init__(self, window_size=5, min_votes=3):
        if window_size < 1:
            raise ValueError("window_size must be positive")

        if not 1 <= min_votes <= window_size:
            raise ValueError("Invalid min_votes")

        self.window_size = window_size
        self.min_votes = min_votes
        self.history = defaultdict(
            lambda: deque(maxlen=self.window_size)
        )

    def update(self, bay_id, state):
        if state not in {"occupied", "empty", "unknown"}:
            raise ValueError(f"Invalid occupancy state: {state}")

        history = self.history[bay_id]
        history.append(state)

        occupied_votes = history.count("occupied")
        empty_votes = history.count("empty")

        if occupied_votes >= self.min_votes:
            decision = "occupied"

        elif (
            empty_votes >= self.min_votes
            and occupied_votes == 0
        ):
            decision = "empty"

        else:
            decision = "unknown"

        return {
            "bay_id": bay_id,
            "state": decision,
            "available": decision == "empty",
            "observations": len(history),
            "occupied_votes": occupied_votes,
            "empty_votes": empty_votes,
        }
