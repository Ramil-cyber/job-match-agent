import re
import unittest
from pathlib import Path

from report_validation import validate_job_match_report

SAMPLE_REPORT_PATH = (
    Path(__file__).resolve().parents[1] / "examples" / "sample_job_match_report.md"
)


class ReportValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid_report = SAMPLE_REPORT_PATH.read_text(encoding="utf-8")

    def test_complete_report_passes(self):
        result = validate_job_match_report(self.valid_report)

        self.assertEqual(result, self.valid_report.strip())

    def test_empty_report_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty report"):
            validate_job_match_report("")

    def test_missing_heading_is_rejected(self):
        incomplete_report = self.valid_report.replace(
            "## Overall Fit",
            "## Fit",
            1,
        )

        with self.assertRaisesRegex(ValueError, "Overall Fit"):
            validate_job_match_report(incomplete_report)

    def test_wrong_section_order_is_rejected(self):
        reordered_report = self.valid_report.replace(
            "## Overall Fit",
            "## TEMPORARY HEADING",
            1,
        )
        reordered_report = reordered_report.replace(
            "## Requirement Matches",
            "## Overall Fit",
            1,
        )
        reordered_report = reordered_report.replace(
            "## TEMPORARY HEADING",
            "## Requirement Matches",
            1,
        )

        with self.assertRaisesRegex(ValueError, "required order"):
            validate_job_match_report(reordered_report)

    def test_missing_interview_question_is_rejected(self):
        incomplete_report = re.sub(
            r"(?m)^\s*5\.\s+.*$",
            "",
            self.valid_report,
        )

        with self.assertRaisesRegex(
            ValueError,
            "exactly five numbered",
        ):
            validate_job_match_report(incomplete_report)


if __name__ == "__main__":
    unittest.main()
