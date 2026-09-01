import unittest

from wce.contracts.scientific import BOOTSTRAP_REPLICATES, BOOTSTRAP_SEED, TRAINING_SEED, selected_rounds


class ScientificContractTest(unittest.TestCase):
    def test_locked_constants(self):
        self.assertEqual(TRAINING_SEED, 20260127)
        self.assertEqual(BOOTSTRAP_SEED, 20260825)
        self.assertEqual(BOOTSTRAP_REPLICATES, 2000)

    def test_middle_pair_rounding(self):
        self.assertEqual(selected_rounds([7, 10, 11, 50]), 11)
        self.assertEqual(selected_rounds([8, 9, 10, 20]), 10)


if __name__ == "__main__":
    unittest.main()

