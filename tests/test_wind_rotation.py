import unittest

import numpy as np

from wce.contracts.scientific import reconstruct_wind, rotate_along_cross_to_uv


class WindRotationTest(unittest.TestCase):
    def test_def1_rotation(self):
        u_residual, v_residual = rotate_along_cross_to_uv([2], [3], [0], [1])
        np.testing.assert_allclose(u_residual, [-3])
        np.testing.assert_allclose(v_residual, [2])

    def test_vector_speed_after_reconstruction(self):
        u, v, speed = reconstruct_wind([1], [2], [2], [3], [0], [1])
        np.testing.assert_allclose(u, [-2])
        np.testing.assert_allclose(v, [4])
        np.testing.assert_allclose(speed, [np.sqrt(20)])


if __name__ == "__main__":
    unittest.main()

