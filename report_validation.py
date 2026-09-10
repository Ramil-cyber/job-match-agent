import re

REQUIRED_HEADINGS = (
    "# Job Match Report",
    "## Overall Fit",
    "## Requirement Matches",
    "## Missing or Weak Qualifications",
    "## Truthful Resume Improvements",
    "## Likely Interview Questions",
)


def _find_heading(report: str, heading: str):
    """Find exactly one occurrence of a required Markdown heading."""

    matches = list(
        re.finditer(
            rf"^{re.escape(heading)}[ \t]*$",
            report,
            flags=re.MULTILINE,
        )
    )

    if len(matches) != 1:
        section_name = heading.lstrip("#").strip()

        raise ValueError(
            f"The report must contain exactly one " f"'{section_name}' heading."
        )

    return matches[0]


def _is_table_separator(line: str) -> bool:
    """Check whether a line is a valid Markdown table separator."""

    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]

    return len(cells) >= 2 and all(
        re.fullmatch(
            r":?-{3,}:?",
            cell.replace(" ", ""),
        )
        for cell in cells
    )


def validate_job_match_report(report: object) -> str:
    """Validate and return a complete job-match report."""

    if not isinstance(report, str) or not report.strip():
        raise ValueError("The agent returned an empty report.")

    cleaned_report = report.strip()

    heading_matches = [
        _find_heading(cleaned_report, heading) for heading in REQUIRED_HEADINGS
    ]

    heading_positions = [match.start() for match in heading_matches]

    if heading_positions != sorted(heading_positions):
        raise ValueError("The report sections are not in the required order.")

    for index in range(1, len(heading_matches)):
        section_start = heading_matches[index].end()

        if index + 1 < len(heading_matches):
            section_end = heading_matches[index + 1].start()
        else:
            section_end = len(cleaned_report)

        if not cleaned_report[section_start:section_end].strip():
            section_name = REQUIRED_HEADINGS[index].lstrip("#").strip()

            raise ValueError(f"The '{section_name}' section is empty.")

    requirement_index = REQUIRED_HEADINGS.index("## Requirement Matches")

    requirement_section = cleaned_report[
        heading_matches[requirement_index]
        .end() : heading_matches[requirement_index + 1]
        .start()
    ]

    table_lines = [
        line.strip()
        for line in requirement_section.splitlines()
        if line.strip().startswith("|")
    ]

    if len(table_lines) < 3 or not _is_table_separator(table_lines[1]):
        raise ValueError(
            "The Requirement Matches section must contain "
            "a populated Markdown table."
        )

    interview_index = REQUIRED_HEADINGS.index("## Likely Interview Questions")

    interview_section = cleaned_report[heading_matches[interview_index].end() :]

    question_numbers = re.findall(
        r"(?m)^\s*(\d+)\.\s+\S",
        interview_section,
    )

    if question_numbers != ["1", "2", "3", "4", "5"]:
        raise ValueError(
            "The report must contain exactly five numbered " "interview questions."
        )

    return cleaned_report
