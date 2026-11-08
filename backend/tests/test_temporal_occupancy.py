import pytest

from worker.inference.temporal_occupancy import TemporalOccupancyEngine


def test_requires_three_votes_before_classification():
    engine = TemporalOccupancyEngine()

    assert engine.update("A01", "empty")["state"] == "unknown"
    assert engine.update("A01", "empty")["state"] == "unknown"

    result = engine.update("A01", "empty")

    assert result["state"] == "empty"
    assert result["available"] is True


def test_occupied_prediction_immediately_withdraws_availability():
    engine = TemporalOccupancyEngine()

    for _ in range(5):
        engine.update("A01", "empty")

    result = engine.update("A01", "occupied")

    assert result["state"] == "unknown"
    assert result["available"] is False


def test_occupied_requires_three_votes():
    engine = TemporalOccupancyEngine()

    for _ in range(2):
        assert engine.update("A01", "occupied")["state"] == "unknown"

    result = engine.update("A01", "occupied")

    assert result["state"] == "occupied"
    assert result["available"] is False


def test_unknown_predictions_do_not_create_availability():
    engine = TemporalOccupancyEngine()

    for _ in range(5):
        result = engine.update("A01", "unknown")

    assert result["state"] == "unknown"
    assert result["available"] is False


def test_history_is_isolated_per_bay():
    engine = TemporalOccupancyEngine()

    for _ in range(3):
        engine.update("A01", "occupied")

    result = engine.update("A02", "empty")

    assert result["state"] == "unknown"
    assert result["observations"] == 1


def test_departure_requires_confirmed_empty_window():
    engine = TemporalOccupancyEngine()

    for _ in range(5):
        engine.update("A01", "occupied")

    for _ in range(4):
        result = engine.update("A01", "empty")
        assert result["available"] is False

    result = engine.update("A01", "empty")

    assert result["state"] == "empty"
    assert result["available"] is True


@pytest.mark.parametrize("state", ["vacant", "", None])
def test_invalid_state_rejected(state):
    engine = TemporalOccupancyEngine()

    with pytest.raises(ValueError):
        engine.update("A01", state)
