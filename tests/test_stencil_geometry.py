import unittest

import numpy as np

from wce.stencil.backend import deduplicate_cells, interpolate_four, locate_four_cells


class StencilGeometryTest(unittest.TestCase):
    def test_four_cells_and_weights(self):
        location = locate_four_cells(np.array([0, 1, 2]), np.array([2, 1, 0]), np.array([0.25]), np.array([0.75]))[0]
        self.assertTrue(location["valid"])
        self.assertEqual(len(location["cells"]), 4)
        self.assertAlmostEqual(sum(location["weights"]), 1.0, places=12)

    def test_boundary_outside_and_deduplication(self):
        locations = locate_four_cells(np.array([0, 1, 2]), np.array([0, 1, 2]), np.array([0.5, 0.5, -1]), np.array([0.5, 0.5, 0.5]))
        self.assertEqual(len(deduplicate_cells(locations)), 4)
        self.assertFalse(locations[-1]["valid"])

    def test_interpolation(self):
        self.assertAlmostEqual(float(interpolate_four([1, 2, 3, 4], [0.25] * 4)), 2.5)


if __name__ == "__main__":
    unittest.main()

