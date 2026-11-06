
import math
import unittest

from worker.inference.occupancy_policy import (
    OccupancyState,
    decide_occupancy,
)


class TestOccupancyPolicy(unittest.TestCase):

    def test_empty_boundary(self):
        for probability in (0.0, 0.10):
            with self.subTest(probability=probability):
                result = decide_occupancy(probability)
                self.assertEqual(result.state, OccupancyState.EMPTY)
                self.assertTrue(result.available)

    def test_unknown_interval(self):
        for probability in (0.1001, 0.4853, 0.6864, 0.8999):
            with self.subTest(probability=probability):
                result = decide_occupancy(probability)
                self.assertEqual(result.state, OccupancyState.UNKNOWN)
                self.assertFalse(result.available)

    def test_occupied_boundary(self):
        for probability in (0.90, 1.0):
            with self.subTest(probability=probability):
                result = decide_occupancy(probability)
                self.assertEqual(result.state, OccupancyState.OCCUPIED)
                self.assertFalse(result.available)

    def test_invalid_probabilities(self):
        for probability in (
            -0.01,
            1.01,
            math.nan,
            math.inf,
            -math.inf,
        ):
            with self.subTest(probability=probability):
                with self.assertRaises(ValueError):
                    decide_occupancy(probability)

    def test_invalid_thresholds(self):
        for empty, occupied in (
            (0.9, 0.1),
            (0.5, 0.5),
            (-0.1, 0.9),
            (0.1, 1.1),
        ):
            with self.subTest(empty=empty, occupied=occupied):
                with self.assertRaises(ValueError):
                    decide_occupancy(
                        0.5,
                        empty_threshold=empty,
                        occupied_threshold=occupied,
                    )

    def test_custom_thresholds(self):
        result = decide_occupancy(
            0.15,
            empty_threshold=0.2,
            occupied_threshold=0.8,
        )
        self.assertEqual(result.state, OccupancyState.EMPTY)
        self.assertTrue(result.available)


if __name__ == "__main__":
    unittest.main()
