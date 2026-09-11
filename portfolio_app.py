from pathlib import Path

import streamlit as st

from pdf_utils import create_job_match_pdf
from quality_benchmark import (
    EXPECTED_ASSESSMENTS,
    calculate_metrics,
    extract_assessments,
)
from report_validation import validate_job_match_report


PROJECT_ROOT = Path(__file__).resolve().parent
SAMPLE_RESUME_PATH = PROJECT_ROOT / "examples" / "sample_resume.txt"
SAMPLE_JOB_PATH = PROJECT_ROOT / "examples" / "sample_job_description.txt"
SAMPLE_REPORT_PATH = PROJECT_ROOT / "examples" / "sample_job_match_report.md"


@st.cache_data
def load_sample_files() -> tuple[str, str, str]:
    """Load and validate the fictional OpenAI portfolio example."""

    sample_resume = SAMPLE_RESUME_PATH.read_text(encoding="utf-8")
    sample_job = SAMPLE_JOB_PATH.read_text(encoding="utf-8")
    sample_report = validate_job_match_report(
        SAMPLE_REPORT_PATH.read_text(encoding="utf-8")
    )
    return sample_resume, sample_job, sample_report


def render_report_downloads(report: str, file_prefix: str) -> None:
    """Display PDF and Markdown downloads for one validated report."""

    pdf_report = create_job_match_pdf(report)
    pdf_column, markdown_column = st.columns(2)

    with pdf_column:
        st.download_button(
            label="Download PDF",
            data=pdf_report,
            file_name=f"{file_prefix}.pdf",
            mime="application/pdf",
            on_click="ignore",
            icon=":material/picture_as_pdf:",
            width="stretch",
        )

    with markdown_column:
        st.download_button(
            label="Download Markdown",
            data=report + "\n",
            file_name=f"{file_prefix}.md",
            mime="text/markdown",
            on_click="ignore",
            icon=":material/download:",
            width="stretch",
        )


st.set_page_config(
    page_title="Job Match Agent Portfolio",
    page_icon="📄",
    layout="centered",
)

sample_resume, sample_job, sample_report = load_sample_files()

st.title("Job Match Agent")
st.write(
    "Explore an OpenAI-powered, evidence-based resume and job-description "
    "matching system through a fictional portfolio example."
)
st.info(
    "The public portfolio displays a saved OpenAI report and makes no live API "
    "call. Live analysis remains available only in the private deployment while "
    "authentication and usage limits are being developed."
)

report_tab, evaluation_tab, about_tab = st.tabs(
    [
        "View OpenAI Example",
        "Quality Evaluation",
        "How It Works",
    ]
)


with report_tab:
    st.subheader("Pre-generated OpenAI report")
    st.caption(
        "The resume, job description, and report are fictional and safe for "
        "public demonstration."
    )

    with st.expander("View the fictional sample inputs"):
        st.markdown("#### Resume")
        st.code(sample_resume, language=None)
        st.markdown("#### Job description")
        st.code(sample_job, language=None)

    st.markdown(sample_report)
    render_report_downloads(sample_report, "sample_openai_job_match_report")
    st.caption(
        "AI-generated guidance. Verify every result before using it in a job "
        "application."
    )


with evaluation_tab:
    st.subheader("Human-labeled quality evaluation")
    st.info(
        "This reproducible smoke test compares the saved OpenAI report with "
        "eight human-labeled expected assessments. Opening this tab makes no "
        "API call."
    )

    openai_assessments = extract_assessments(sample_report)
    metrics = calculate_metrics(openai_assessments)
    st.table(
        [
            {
                "Requirement": requirement,
                "Expected": expected,
                "OpenAI": actual,
            }
            for (requirement, expected), actual in zip(
                EXPECTED_ASSESSMENTS,
                openai_assessments,
            )
        ]
    )

    accuracy_column, false_positive_column, missed_match_column = st.columns(3)
    accuracy_column.metric(
        "Expected labels matched",
        f"{metrics['correct']}/{metrics['total']}",
    )
    false_positive_column.metric(
        "False qualification claims",
        metrics["false_positive_claims"],
    )
    missed_match_column.metric(
        "Missed demonstrated matches",
        metrics["missed_demonstrated_matches"],
    )

    st.warning(
        "This result covers one fictional scenario and is not a general 100% "
        "accuracy claim. Results for other resumes and job descriptions can differ."
    )


with about_tab:
    st.subheader("One OpenAI analysis workflow")
    st.markdown(
        """
- **Private live agent:** Uses OpenAI for requirement matching, evidence-based
  reasoning, resume suggestions, and interview questions.
- **Public portfolio:** Displays a validated, pre-generated OpenAI report without
  accepting user data or exposing an API key.
- **Guardrails:** Uses only resume evidence, separates matches from gaps, rejects
  incomplete reports, and supports PDF and Markdown downloads.
        """
    )
    st.warning(
        "This project is a portfolio demonstration, not an automated hiring "
        "decision system. Results require human review."
    )
    st.link_button(
        "View source code on GitHub",
        "https://github.com/Ramil-cyber/job-match-agent",
        icon=":material/code:",
        width="stretch",
    )
