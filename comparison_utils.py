"""Utilities for comparing two validated job-match reports."""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from report_validation import validate_job_match_report


@dataclass(frozen=True)
class ReportAssessment:
    requirement: str
    assessment: str


@dataclass(frozen=True)
class ComparisonRow:
    requirement: str
    free_assessment: str
    openai_assessment: str

    @property
    def agrees(self) -> bool:
        return (
            self.free_assessment == self.openai_assessment
            and self.free_assessment not in {"Not reported", "Other"}
        )

    @property
    def comparable(self) -> bool:
        return (
            self.free_assessment not in {"Not reported", "Other"}
            and self.openai_assessment not in {"Not reported", "Other"}
        )


def normalize_assessment(assessment: str) -> str:
    """Normalize varied report wording without treating agreement as accuracy."""

    lowered = assessment.casefold()
    if any(word in lowered for word in ("partial", "weak", "limited")):
        return "Partial"
    if any(
        phrase in lowered
        for phrase in (
            "missing",
            "not demonstrated",
            "not found",
            "no evidence",
            "unmet",
        )
    ):
        return "Missing"
    if any(
        phrase in lowered
        for phrase in ("meets", "demonstrated", "strong match")
    ):
        return "Meets"
    return "Other"


def _split_table_row(line: str) -> list[str]:
    return [
        cell.replace(r"\|", "|").strip()
        for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))
    ]


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells
    )


def _clean_requirement(requirement: str) -> str:
    cleaned = requirement.replace("**", "").strip()
    return re.sub(r"^(?:required|preferred)\s*:\s*", "", cleaned, flags=re.I)


def extract_report_assessments(report: str) -> list[ReportAssessment]:
    """Extract normalized requirement assessments from a validated report."""

    validated_report = validate_job_match_report(report)
    table_section = validated_report.split(
        "## Requirement Matches", 1
    )[1].split("## Missing or Weak Qualifications", 1)[0]

    assessments = []
    for line in table_section.splitlines():
        if not line.strip().startswith("|"):
            continue

        cells = _split_table_row(line)
        if len(cells) != 3:
            continue
        if cells[0].casefold() == "requirement" or _is_separator_row(cells):
            continue

        assessments.append(
            ReportAssessment(
                requirement=_clean_requirement(cells[0]),
                assessment=normalize_assessment(cells[2]),
            )
        )

    if not assessments:
        raise ValueError("No requirement assessments were found in the report table.")
    return assessments


def _requirement_similarity(first: str, second: str) -> float:
    first_normalized = re.sub(r"[^a-z0-9]+", " ", first.casefold()).strip()
    second_normalized = re.sub(r"[^a-z0-9]+", " ", second.casefold()).strip()
    first_tokens = set(first_normalized.split())
    second_tokens = set(second_normalized.split())

    union = first_tokens | second_tokens
    token_score = len(first_tokens & second_tokens) / len(union) if union else 0.0
    sequence_score = SequenceMatcher(
        None,
        first_normalized,
        second_normalized,
    ).ratio()
    return (0.65 * token_score) + (0.35 * sequence_score)


def compare_report_assessments(
    free_report: str,
    openai_report: str,
) -> list[ComparisonRow]:
    """Align report rows and compare their normalized assessment labels."""

    free_rows = extract_report_assessments(free_report)
    openai_rows = extract_report_assessments(openai_report)
    available_openai_indexes = set(range(len(openai_rows)))
    comparison_rows = []

    for free_index, free_row in enumerate(free_rows):
        scored_indexes = [
            (
                _requirement_similarity(
                    free_row.requirement,
                    openai_rows[index].requirement,
                ),
                index,
            )
            for index in available_openai_indexes
        ]

        if scored_indexes:
            best_score, best_index = max(scored_indexes)
        else:
            best_score, best_index = 0.0, None

        # Reports normally preserve job-description order. Use the same-position
        # row as a conservative fallback only when both tables have equal length.
        if (
            best_score < 0.18
            and len(free_rows) == len(openai_rows)
            and free_index in available_openai_indexes
        ):
            best_index = free_index
            best_score = 0.18

        if best_index is None or best_score < 0.18:
            openai_assessment = "Not reported"
        else:
            openai_assessment = openai_rows[best_index].assessment
            available_openai_indexes.remove(best_index)

        comparison_rows.append(
            ComparisonRow(
                requirement=free_row.requirement,
                free_assessment=free_row.assessment,
                openai_assessment=openai_assessment,
            )
        )

    for index in sorted(available_openai_indexes):
        openai_row = openai_rows[index]
        comparison_rows.append(
            ComparisonRow(
                requirement=f"OpenAI only: {openai_row.requirement}",
                free_assessment="Not reported",
                openai_assessment=openai_row.assessment,
            )
        )

    return comparison_rows


def agreement_summary(rows: list[ComparisonRow]) -> tuple[int, int]:
    """Return the number of agreements and comparable requirement rows."""

    comparable_rows = [row for row in rows if row.comparable]
    agreements = sum(row.agrees for row in comparable_rows)
    return agreements, len(comparable_rows)
