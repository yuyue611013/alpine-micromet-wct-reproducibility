import unittest

import numpy as np

from wce.contracts.scientific import ContractError, convert_ssrd_to_wm2


class SSRDUnitTest(unittest.TestCase):
    def test_divides_before_use(self):
        np.testing.assert_allclose(convert_ssrd_to_wm2([0, 3600, 7200], "J m**-2"), [0, 1, 2])

    def test_unknown_units_stop(self):
        with self.assertRaises(ContractError):
            convert_ssrd_to_wm2([1], "unknown")


if __name__ == "__main__":
    unittest.main()

