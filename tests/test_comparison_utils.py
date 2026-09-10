import unittest
from pathlib import Path

from comparison_utils import (
    agreement_summary,
    compare_report_assessments,
    extract_report_assessments,
    normalize_assessment,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_REPORT_PATH = (
    PROJECT_ROOT / "examples" / "sample_job_match_report.md"
)


def make_report(rows):
    table_rows = "\n".join(
        f"| {requirement} | Evidence | {assessment} |"
        for requirement, assessment in rows
    )
    return f"""# Job Match Report

## Overall Fit
Moderate.

## Requirement Matches

| Requirement | Resume Evidence | Assessment |
|---|---|---|
{table_rows}

## Missing or Weak Qualifications
- Review the comparison.

## Truthful Resume Improvements
- Add accurate details where appropriate.

## Likely Interview Questions
1. Question one?
2. Question two?
3. Question three?
4. Question four?
5. Question five?
"""


class ComparisonUtilityTests(unittest.TestCase):
    def test_assessment_wording_is_normalized(self):
        self.assertEqual(normalize_assessment("Meets"), "Meets")
        self.assertEqual(
            normalize_assessment("Partially demonstrated; more detail needed"),
            "Partial",
        )
        self.assertEqual(normalize_assessment("Not demonstrated"), "Missing")

    def test_saved_openai_report_has_eight_assessments(self):
        report = SAMPLE_REPORT_PATH.read_text(encoding="utf-8")

        assessments = extract_report_assessments(report)

        self.assertEqual(len(assessments), 8)
        self.assertEqual(assessments[0].assessment, "Meets")
        self.assertEqual(assessments[4].assessment, "Missing")

    def test_paraphrased_and_reordered_requirements_are_aligned(self):
        free_report = make_report(
            [
                ("**Required:** Strong Python and SQL skills", "Meets"),
                ("**Required:** Experience using AWS", "Not demonstrated"),
            ]
        )
        openai_report = make_report(
            [
                ("AWS cloud services experience", "Missing"),
                ("Strong SQL and Python skills", "Meets"),
            ]
        )

        rows = compare_report_assessments(free_report, openai_report)
        agreements, comparable = agreement_summary(rows)

        self.assertEqual(len(rows), 2)
        self.assertEqual(agreements, 2)
        self.assertEqual(comparable, 2)

    def test_extra_openai_requirement_is_reported(self):
        free_report = make_report([("Python", "Meets")])
        openai_report = make_report(
            [("Python", "Meets"), ("AWS", "Missing")]
        )

        rows = compare_report_assessments(free_report, openai_report)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1].free_assessment, "Not reported")
        self.assertEqual(rows[1].openai_assessment, "Missing")


if __name__ == "__main__":
    unittest.main()
