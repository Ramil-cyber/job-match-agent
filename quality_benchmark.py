"""Compare the public analyzer with a saved OpenAI example.

This benchmark uses one fictional, human-labeled scenario. It makes no OpenAI
API call. The result is a smoke test, not a general accuracy claim.
"""

from pathlib import Path

from fastembed import TextEmbedding

from report_validation import validate_job_match_report
from semantic_analyzer import create_semantic_job_match_report


PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_NAME = "BAAI/bge-small-en-v1.5"
SAMPLE_RESUME_PATH = PROJECT_ROOT / "examples" / "sample_resume.txt"
SAMPLE_JOB_PATH = PROJECT_ROOT / "examples" / "sample_job_description.txt"
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
    """Read assessment values from a validated report table."""

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

    if len(assessments) != len(EXPECTED_ASSESSMENTS):
        raise ValueError(
            "The benchmark expected exactly "
            f"{len(EXPECTED_ASSESSMENTS)} requirement rows but found "
            f"{len(assessments)}."
        )
    return assessments


def calculate_metrics(predicted: list[str]) -> dict[str, int | float]:
    """Calculate transparent classification and safety metrics."""

    expected = [assessment for _, assessment in EXPECTED_ASSESSMENTS]
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


def print_comparison(
    semantic_assessments: list[str],
    openai_assessments: list[str],
    engine_name: str,
) -> None:
    """Print a readable benchmark table and an honest interpretation."""

    expected = [assessment for _, assessment in EXPECTED_ASSESSMENTS]
    semantic_metrics = calculate_metrics(semantic_assessments)
    openai_metrics = calculate_metrics(openai_assessments)

    print("Quality benchmark: one labeled fictional scenario")
    print(f"Public analysis engine: {engine_name}")
    print()
    print(f"{'Requirement':<38} {'Expected':<9} {'Free':<9} {'OpenAI':<9}")
    print("-" * 69)
    for (label, _), expected_value, semantic_value, openai_value in zip(
        EXPECTED_ASSESSMENTS,
        expected,
        semantic_assessments,
        openai_assessments,
    ):
        print(
            f"{label:<38} {expected_value:<9} "
            f"{semantic_value:<9} {openai_value:<9}"
        )

    print()
    print(
        "Free semantic classification accuracy: "
        f"{semantic_metrics['correct']}/{semantic_metrics['total']} "
        f"({semantic_metrics['accuracy']:.0%})"
    )
    print(
        "Saved OpenAI classification accuracy: "
        f"{openai_metrics['correct']}/{openai_metrics['total']} "
        f"({openai_metrics['accuracy']:.0%})"
    )
    print(
        "Free semantic false-positive qualification claims: "
        f"{semantic_metrics['false_positive_claims']}"
    )
    print(
        "Saved OpenAI false-positive qualification claims: "
        f"{openai_metrics['false_positive_claims']}"
    )
    print()
    print(
        "Interpretation: This checks requirement classification and unsupported "
        "qualification claims. The OpenAI report may still provide richer, more "
        "context-aware explanations than the templated free report. Because this "
        "benchmark contains one scenario, do not treat its percentage as a general "
        "accuracy estimate."
    )


def main() -> None:
    """Run the no-cost comparison using the repository's fictional example."""

    resume = SAMPLE_RESUME_PATH.read_text(encoding="utf-8")
    job_description = SAMPLE_JOB_PATH.read_text(encoding="utf-8")
    openai_report = OPENAI_REPORT_PATH.read_text(encoding="utf-8")

    embedding_model = TextEmbedding(model_name=MODEL_NAME)
    semantic_report, engine_name = create_semantic_job_match_report(
        resume,
        job_description,
        embedding_model,
    )

    semantic_assessments = extract_assessments(semantic_report)
    openai_assessments = extract_assessments(openai_report)
    print_comparison(semantic_assessments, openai_assessments, engine_name)


if __name__ == "__main__":
    main()
