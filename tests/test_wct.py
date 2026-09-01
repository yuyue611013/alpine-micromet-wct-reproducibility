import unittest

import numpy as np

from wce.contracts.scientific import wct_celsius, wct_piecewise_sensitivity


class WCTTest(unittest.TestCase):
    def test_standard_formula_and_floor(self):
        temperature = -10.0
        wind_ms = 10.0
        wind_kmh = 36.0
        expected = 13.12 + 0.6215 * temperature - 11.37 * wind_kmh**0.16 + 0.3965 * temperature * wind_kmh**0.16
        self.assertAlmostEqual(float(wct_celsius([temperature], [wind_ms])[0]), expected)
        self.assertTrue(np.isfinite(wct_celsius([temperature], [0.0])[0]))

    def test_piecewise_is_separate(self):
        primary = wct_celsius([-5.0], [0.0])[0]
        sensitivity = wct_piecewise_sensitivity([-5.0], [0.0])[0]
        self.assertNotEqual(float(primary), float(sensitivity))
        self.assertEqual(float(sensitivity), -5.0)


if __name__ == "__main__":
    unittest.main()

