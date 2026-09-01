import unittest
from pathlib import Path

from wce.pipeline.public_validation import validate_public_repository


class PublicSafetyTest(unittest.TestCase):
    def test_repository_public_data_boundary(self):
        root = Path(__file__).resolve().parents[1]
        result = validate_public_repository(root)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["identifying_or_row_key_files"], 0)


if __name__ == "__main__":
    unittest.main()

