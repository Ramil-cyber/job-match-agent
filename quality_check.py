from file_utils import PROJECT_ROOT, read_text_file

REPORT_PATH = PROJECT_ROOT / "outputs" / "job_match_report.md"

REQUIRED_HEADINGS = (
    "# Job Match Report",
    "## Overall Fit",
    "## Requirement Matches",
    "## Missing or Weak Qualifications",
    "## Truthful Resume Improvements",
    "## Likely Interview Questions",
)

GAP_MARKERS = (
    "not found",
    "missing",
    "not demonstrated",
    "not clearly demonstrated",
    "no evidence",
    "no direct",
    "does not",
    "not met",
    "gap",
)

GAP_ALIASES = {
    "AWS": ("aws",),
    "NLP": ("natural language processing", "nlp"),
}


def skill_is_marked_as_gap(
    report: str,
    aliases: tuple[str, ...],
) -> bool:
    """Check whether a skill is described as missing or weak."""

    relevant_lines = [
        line.lower()
        for line in report.splitlines()
        if any(alias in line.lower() for alias in aliases)
    ]

    return any(any(marker in line for marker in GAP_MARKERS) for line in relevant_lines)


def count_interview_questions(report: str) -> int:
    """Count numbered items in the interview-question section."""

    heading = "## Likely Interview Questions"

    if heading not in report:
        return 0

    question_section = report.split(heading, maxsplit=1)[1]
    question_count = 0

    for line in question_section.splitlines():
        cleaned_line = line.strip()
        number, separator, question = cleaned_line.partition(".")

        if separator and number.isdigit() and question.strip():
            question_count += 1

    return question_count


def main() -> None:
    """Run all quality checks and display the results."""

    report = read_text_file(REPORT_PATH)

    checks = {
        "All required headings are present": all(
            heading in report for heading in REQUIRED_HEADINGS
        ),
        "AWS is marked as a gap": skill_is_marked_as_gap(
            report,
            GAP_ALIASES["AWS"],
        ),
        "NLP is marked as a gap": skill_is_marked_as_gap(
            report,
            GAP_ALIASES["NLP"],
        ),
        "Exactly five interview questions are present": count_interview_questions(
            report
        )
        == 5,
    }

    for check_name, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {check_name}")

    if not all(checks.values()):
        raise SystemExit("Quality check failed.")

    print("Quality check passed.")


if __name__ == "__main__":
    main()
