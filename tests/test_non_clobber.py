import tempfile
import unittest
from pathlib import Path

from wce.contracts.io import require_absent, write_text_once
from wce.contracts.scientific import ContractError


class NonClobberTest(unittest.TestCase):
    def test_existing_output_stops(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "result.txt"
            write_text_once(target, "first\n")
            with self.assertRaises(ContractError):
                require_absent(target)
            with self.assertRaises(ContractError):
                write_text_once(target, "second\n")
            self.assertEqual(target.read_text(), "first\n")


if __name__ == "__main__":
    unittest.main()

