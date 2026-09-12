import unittest
from pathlib import Path

from job_match_agent.quality_benchmark import (
    EXPECTED_ASSESSMENTS,
    calculate_metrics,
    extract_assessments,
    normalize_assessment,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_REPORT_PATH = PROJECT_ROOT / "examples" / "sample_job_match_report.md"


class QualityBenchmarkTests(unittest.TestCase):
    def test_assessment_wording_is_normalized(self):
        self.assertEqual(normalize_assessment("Meets"), "Meets")
        self.assertEqual(
            normalize_assessment("Partially demonstrated; more detail needed"),
            "Partial",
        )
        self.assertEqual(normalize_assessment("Not demonstrated"), "Missing")

    def test_unknown_assessment_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unrecognized assessment"):
            normalize_assessment("Unclear")

    def test_saved_openai_report_matches_expected_assessments(self):
        report = SAMPLE_REPORT_PATH.read_text(encoding="utf-8")

        assessments = extract_assessments(report)
        expected = [assessment for _, assessment in EXPECTED_ASSESSMENTS]

        self.assertEqual(assessments, expected)

    def test_perfect_result_has_no_false_positive_or_missed_matches(self):
        predicted = [assessment for _, assessment in EXPECTED_ASSESSMENTS]

        metrics = calculate_metrics(predicted)

        self.assertEqual(metrics["correct"], 8)
        self.assertEqual(metrics["total"], 8)
        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertEqual(metrics["false_positive_claims"], 0)
        self.assertEqual(metrics["missed_demonstrated_matches"], 0)

    def test_false_positive_and_missed_match_are_counted(self):
        predicted = [
            "Missing",
            "Meets",
            "Meets",
            "Meets",
            "Meets",
            "Partial",
            "Missing",
            "Partial",
        ]

        metrics = calculate_metrics(predicted)

        self.assertEqual(metrics["correct"], 6)
        self.assertEqual(metrics["false_positive_claims"], 1)
        self.assertEqual(metrics["missed_demonstrated_matches"], 1)

    def test_wrong_number_of_assessments_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Expected 8 assessments"):
            calculate_metrics(["Meets"])


if __name__ == "__main__":
    unittest.main()
