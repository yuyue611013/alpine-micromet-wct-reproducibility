import math
import unittest

from tools.verify_reference_outputs import assert_full_precision_close


class ReferenceToleranceRegressionTest(unittest.TestCase):
    def test_adjacent_serialized_floats_are_tolerance_safe(self):
        expected = {
            "dewpoint": [4.6285555175781825],
            "external_temperature": [3.8870070044078937],
        }
        actual = {
            "dewpoint": [4.628555517578183],
            "external_temperature": [3.887007004407893],
        }
        assert_full_precision_close(expected, actual)

    def test_structure_and_nonfinite_values_still_fail(self):
        with self.assertRaises(RuntimeError):
            assert_full_precision_close({"x": [1.0]}, {"x": [1.0, 2.0]})
        for nonfinite in (math.nan, math.inf, -math.inf):
            with self.assertRaises(RuntimeError):
                assert_full_precision_close({"x": [1.0]}, {"x": [nonfinite]})


if __name__ == "__main__":
    unittest.main()
