import unittest
from pathlib import Path

from job_match_agent.pdf_utils import create_job_match_pdf
from job_match_agent.report_validation import validate_job_match_report

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_REPORT_PATH = PROJECT_ROOT / "examples" / "sample_job_match_report.md"


class PDFUtilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample_report = SAMPLE_REPORT_PATH.read_text(encoding="utf-8")

    def test_complete_report_creates_pdf_bytes(self):
        validated_report = validate_job_match_report(self.sample_report)

        pdf_data = create_job_match_pdf(validated_report)

        self.assertIsInstance(pdf_data, bytes)
        self.assertTrue(pdf_data.startswith(b"%PDF-"))
        self.assertIn(b"%%EOF", pdf_data[-1024:])
        self.assertGreater(len(pdf_data), 1000)

    def test_empty_report_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "The report cannot be empty",
        ):
            create_job_match_pdf("   ")


if __name__ == "__main__":
    unittest.main()
