import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DualLicenseBoundaryTest(unittest.TestCase):
    def test_mit_license_and_confirmed_holder(self):
        text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("MIT License\n\nCopyright (c) 2026 Yu Yue, Yannis P. Pitsiladis, and contributors\n"))
        self.assertIn('THE SOFTWARE IS PROVIDED "AS IS"', text)
        self.assertIn("OTHER DEALINGS IN THE\nSOFTWARE.", text)

    def test_cc_by_scope_is_explicit_and_narrow(self):
        text = (ROOT / "DATA_LICENSE.md").read_text(encoding="utf-8")
        for path in ("data/aggregate/", "data/figure_source/", "reference_outputs/tables/"):
            self.assertIn(path, text)
        self.assertIn("https://creativecommons.org/licenses/by/4.0/", text)
        self.assertIn("does **not** license", text)
        self.assertIn("third-party data", text)
        self.assertIn("permission-controlled external observations", text)

    def test_third_party_and_citation_boundaries(self):
        boundary = (ROOT / "THIRD_PARTY_DATA.md").read_text(encoding="utf-8")
        citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        for phrase in ("Copernicus license", "does not redistribute raw ERA5-Land NetCDF", "WeatherXM", "Olympic venue hourly observations", "Model files, production models, station-hour predictions"):
            self.assertIn(phrase, boundary)
        self.assertIn("GitHub repository URL:", citation)
        self.assertIn("Zenodo DOI:", citation)
        self.assertNotIn("orcid:", citation.lower())


if __name__ == "__main__":
    unittest.main()
