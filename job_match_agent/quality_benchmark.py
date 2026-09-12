"""Evaluate the saved OpenAI report against human-labeled expectations.

This benchmark uses one fictional scenario and makes no OpenAI API call. It is
a reproducible smoke test, not a general accuracy claim.
"""

from pathlib import Path

from .report_validation import validate_job_match_report

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OPENAI_REPORT_PATH = PROJECT_ROOT / "examples" / "sample_job_match_report.md"

EXPECTED_ASSESSMENTS = (
    ("Quantitative bachelor's degree", "Meets"),
    ("Two years of analytics experience", "Meets"),
    ("Python and SQL", "Meets"),
    ("Forecasting or machine learning", "Meets"),
    ("AWS", "Missing"),
    ("Written and verbal communication", "Partial"),
    ("Natural language processing", "Missing"),
    ("Executive dashboards", "Partial"),
)


def normalize_assessment(assessment: str) -> str:
    """Map report wording to the three human-labeled benchmark classes."""

    lowered = assessment.casefold()
    if "partial" in lowered:
        return "Partial"
    if "missing" in lowered or "not demonstrated" in lowered:
        return "Missing"
    if "meets" in lowered:
        return "Meets"
    raise ValueError(f"Unrecognized assessment: {assessment}")


def extract_assessments(report: str) -> list[str]:
    """Read assessment values from a validated OpenAI report table."""

    validated_report = validate_job_match_report(report)
    table_section = validated_report.split(
        "## Requirement Matches", 1
    )[1].split("## Missing or Weak Qualifications", 1)[0]

    assessments = []
    for line in table_section.splitlines():
        if not line.strip().startswith("|"):
            continue

        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[0] in {"Requirement", "---"}:
            continue
        if all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue

        assessments.append(normalize_assessment(cells[2]))

    expected_count = len(EXPECTED_ASSESSMENTS)
    if len(assessments) != expected_count:
        raise ValueError(
            f"The benchmark expected exactly {expected_count} requirement rows "
            f"but found {len(assessments)}."
        )
    return assessments


def calculate_metrics(predicted: list[str]) -> dict[str, int | float]:
    """Calculate classification and unsupported-claim metrics."""

    expected = [assessment for _, assessment in EXPECTED_ASSESSMENTS]
    if len(predicted) != len(expected):
        raise ValueError(
            f"Expected {len(expected)} assessments but received {len(predicted)}."
        )

    correct = sum(
        predicted_assessment == expected_assessment
        for predicted_assessment, expected_assessment in zip(predicted, expected)
    )
    false_positive_claims = sum(
        expected_assessment == "Missing" and predicted_assessment != "Missing"
        for predicted_assessment, expected_assessment in zip(predicted, expected)
    )
    missed_demonstrated_matches = sum(
        expected_assessment == "Meets" and predicted_assessment == "Missing"
        for predicted_assessment, expected_assessment in zip(predicted, expected)
    )
    return {
        "correct": correct,
        "total": len(expected),
        "accuracy": correct / len(expected),
        "false_positive_claims": false_positive_claims,
        "missed_demonstrated_matches": missed_demonstrated_matches,
    }


def print_results(openai_assessments: list[str]) -> None:
    """Print the OpenAI-only benchmark and an honest interpretation."""

    expected = [assessment for _, assessment in EXPECTED_ASSESSMENTS]
    metrics = calculate_metrics(openai_assessments)

    print("OpenAI quality benchmark: one labeled fictional scenario")
    print()
    print(f"{'Requirement':<38} {'Expected':<9} {'OpenAI':<9}")
    print("-" * 58)
    for (label, _), expected_value, openai_value in zip(
        EXPECTED_ASSESSMENTS,
        expected,
        openai_assessments,
    ):
        print(f"{label:<38} {expected_value:<9} {openai_value:<9}")

    print()
    print(
        "Saved OpenAI classification accuracy: "
        f"{metrics['correct']}/{metrics['total']} ({metrics['accuracy']:.0%})"
    )
    print(
        "Saved OpenAI false-positive qualification claims: "
        f"{metrics['false_positive_claims']}"
    )
    print(
        "Saved OpenAI missed demonstrated matches: "
        f"{metrics['missed_demonstrated_matches']}"
    )
    print()
    print(
        "Interpretation: This checks requirement classification and unsupported "
        "qualification claims for one fictional scenario. Do not treat the "
        "result as a general accuracy estimate."
    )


def main() -> None:
    """Evaluate the repository's saved OpenAI example without making an API call."""

    openai_report = OPENAI_REPORT_PATH.read_text(encoding="utf-8")
    openai_assessments = extract_assessments(openai_report)
    print_results(openai_assessments)


if __name__ == "__main__":
    main()
