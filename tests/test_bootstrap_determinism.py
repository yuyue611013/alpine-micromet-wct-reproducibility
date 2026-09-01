import unittest

import pandas as pd

from wce.contracts.scientific import BOOTSTRAP_REPLICATES, BOOTSTRAP_SEED, paired_station_cluster_bootstrap


class BootstrapTest(unittest.TestCase):
    def test_locked_configuration_and_determinism(self):
        self.assertEqual(BOOTSTRAP_REPLICATES, 2000)
        self.assertEqual(BOOTSTRAP_SEED, 20260825)
        frame = pd.DataFrame({"station_id": ["A", "A", "B", "B"], "observed": [0, 1, 2, 3], "background": [1, 2, 2, 4], "corrected": [0, 1, 2, 3]})
        first = paired_station_cluster_bootstrap(frame, "observed", "background", "corrected", replicates=25, seed=BOOTSTRAP_SEED)
        second = paired_station_cluster_bootstrap(frame, "observed", "background", "corrected", replicates=25, seed=BOOTSTRAP_SEED)
        pd.testing.assert_frame_equal(first, second)


if __name__ == "__main__":
    unittest.main()

