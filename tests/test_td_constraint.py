import unittest

import pandas as pd

from wce.contracts.scientific import ContractError, constrain_dewpoint_same_fold


class DewPointConstraintTest(unittest.TestCase):
    def test_same_fold_constraint_retains_unconstrained(self):
        keys = {"station_id": ["A", "B"], "time_utc": ["2025-01-01", "2025-01-01"], "fold": [0, 1]}
        temperature = pd.DataFrame({**keys, "T_corrected": [-3.0, 2.0]})
        dewpoint = pd.DataFrame({**keys, "Td_corrected_unconstrained": [-2.0, 1.0]})
        result = constrain_dewpoint_same_fold(temperature, dewpoint)
        self.assertEqual(result.Td_corrected_unconstrained.tolist(), [-2.0, 1.0])
        self.assertEqual(result.Td_corrected_constrained.tolist(), [-3.0, 1.0])

    def test_fold_mismatch_stops(self):
        temperature = pd.DataFrame({"station_id": ["A"], "time_utc": ["2025-01-01"], "fold": [0], "T_corrected": [0.0]})
        dewpoint = pd.DataFrame({"station_id": ["A"], "time_utc": ["2025-01-01"], "fold": [1], "Td_corrected_unconstrained": [0.0]})
        with self.assertRaises(ContractError):
            constrain_dewpoint_same_fold(temperature, dewpoint)


if __name__ == "__main__":
    unittest.main()

