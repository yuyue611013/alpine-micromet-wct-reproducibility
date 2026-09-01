import unittest

import pandas as pd

from wce.contracts.scientific import nested_fold_plan, validate_station_fold_map


class NestedCVTest(unittest.TestCase):
    def setUp(self):
        self.stations = [f"S{index:03d}" for index in range(74)]
        folds = [0] * 15 + [1] * 15 + [2] * 15 + [3] * 15 + [4] * 14
        self.fold_map = validate_station_fold_map(pd.DataFrame({"station_id": self.stations, "fold": folds}))

    def test_outer_zero_access_and_inner_grouping(self):
        mismatch = set(self.stations[:17])
        plans = nested_fold_plan(self.fold_map, mismatch, True)
        predicted = []
        for plan in plans:
            outer = set(plan["prediction_stations"])
            train = set(plan["final_training_stations"])
            self.assertFalse(outer & train)
            self.assertFalse(train & mismatch)
            self.assertEqual(len(plan["inner_runs"]), 4)
            for inner in plan["inner_runs"]:
                self.assertFalse(outer & (set(inner["training_stations"]) | set(inner["validation_stations"])))
            predicted.extend(outer)
        self.assertEqual(len(predicted), 74)
        self.assertEqual(len(set(predicted)), 74)

    def test_wind_does_not_exclude_mismatch(self):
        plans = nested_fold_plan(self.fold_map, set(self.stations[:17]), False)
        self.assertTrue(any(set(plan["final_training_stations"]) & set(self.stations[:17]) for plan in plans))


if __name__ == "__main__":
    unittest.main()

