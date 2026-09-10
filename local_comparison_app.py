"""Local-only Streamlit app for live semantic and OpenAI comparisons."""

import asyncio
import os
from pathlib import Path

import streamlit as st
from agents import Runner
from dotenv import load_dotenv
from fastembed import TextEmbedding

from agent_core import build_analysis_request, create_job_match_agent
from comparison_utils import agreement_summary, compare_report_assessments
from pdf_utils import create_job_match_pdf
from report_validation import validate_job_match_report
from semantic_analyzer import create_semantic_job_match_report


MAX_INPUT_CHARACTERS = 10_000
MODEL_NAME = "BAAI/bge-small-en-v1.5"
PROJECT_ROOT = Path(__file__).resolve().parent
SAMPLE_RESUME_PATH = PROJECT_ROOT / "examples" / "sample_resume.txt"
SAMPLE_JOB_PATH = PROJECT_ROOT / "examples" / "sample_job_description.txt"


load_dotenv()
openai_agent = create_job_match_agent(save_to_file=False)


@st.cache_resource(show_spinner=False)
def load_embedding_model() -> TextEmbedding:
    """Load one semantic model for the local Streamlit process."""

    return TextEmbedding(model_name=MODEL_NAME)


def render_downloads(report: str, prefix: str) -> None:
    """Render PDF and Markdown downloads for one report."""

    pdf_column, markdown_column = st.columns(2)
    with pdf_column:
        st.download_button(
            "PDF",
            create_job_match_pdf(report),
            file_name=f"{prefix}.pdf",
            mime="application/pdf",
            key=f"{prefix}_pdf",
            on_click="ignore",
            width="stretch",
        )
    with markdown_column:
        st.download_button(
            "Markdown",
            report + "\n",
            file_name=f"{prefix}.md",
            mime="text/markdown",
            key=f"{prefix}_markdown",
            on_click="ignore",
            width="stretch",
        )


st.set_page_config(
    page_title="Local Job Match Comparison",
    page_icon="⚖️",
    layout="wide",
)

state_defaults = {
    "comparison_resume": "",
    "comparison_job": "",
    "comparison_free_report": None,
    "comparison_openai_report": None,
    "comparison_engine": None,
    "comparison_rows": None,
}
for state_key, default_value in state_defaults.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default_value


st.title("Live Job Match Comparison")
st.write(
    "Run the free semantic analyzer and the private OpenAI agent on exactly "
    "the same resume and job description."
)
st.warning(
    "Local/private testing only. Opening this page costs nothing. Each click of "
    "Compare Both makes one paid OpenAI API call. Do not deploy this entry point "
    "as a public app with an API key."
)
st.caption(
    "Privacy: The free report is processed in this app. The OpenAI report sends "
    "the submitted text to the OpenAI API. Neither report is written to a shared file."
)

if st.button("Load fictional example"):
    st.session_state.comparison_resume = SAMPLE_RESUME_PATH.read_text(
        encoding="utf-8"
    )
    st.session_state.comparison_job = SAMPLE_JOB_PATH.read_text(encoding="utf-8")
    st.session_state.comparison_free_report = None
    st.session_state.comparison_openai_report = None
    st.session_state.comparison_rows = None
    st.rerun()


with st.form("live_comparison_form"):
    input_left, input_right = st.columns(2)
    with input_left:
        resume_text = st.text_area(
            "Resume",
            height=320,
            max_chars=MAX_INPUT_CHARACTERS,
            key="comparison_resume",
            placeholder="Paste the resume text here.",
        )
    with input_right:
        job_description_text = st.text_area(
            "Job Description",
            height=320,
            max_chars=MAX_INPUT_CHARACTERS,
            key="comparison_job",
            placeholder="Paste the job description here.",
        )

    submitted = st.form_submit_button(
        "Compare Both",
        type="primary",
        width="stretch",
    )


if submitted:
    st.session_state.comparison_free_report = None
    st.session_state.comparison_openai_report = None
    st.session_state.comparison_engine = None
    st.session_state.comparison_rows = None

    comparison_enabled = (
        os.getenv("ENABLE_PAID_LOCAL_COMPARISON", "").casefold() == "true"
    )

    if not resume_text.strip() or not job_description_text.strip():
        st.error("Please provide both a resume and a job description.")
    elif not comparison_enabled:
        st.error(
            "Paid local comparison is disabled. Add "
            "ENABLE_PAID_LOCAL_COMPARISON=true to your local .env file."
        )
    elif not os.getenv("OPENAI_API_KEY"):
        st.error("The local OPENAI_API_KEY is not configured.")
    else:
        try:
            with st.spinner("Running the free semantic analysis...", show_time=True):
                try:
                    embedding_model = load_embedding_model()
                except Exception:
                    embedding_model = None

                free_report, engine_name = create_semantic_job_match_report(
                    resume_text,
                    job_description_text,
                    embedding_model,
                )
                free_report = validate_job_match_report(free_report)

            request = build_analysis_request(
                resume=resume_text,
                job_description=job_description_text,
            )
            with st.spinner(
                "Running one paid OpenAI analysis...",
                show_time=True,
            ):
                openai_result = asyncio.run(Runner.run(openai_agent, request))
                openai_report = validate_job_match_report(openai_result.final_output)

            comparison_rows = compare_report_assessments(
                free_report,
                openai_report,
            )
            st.session_state.comparison_free_report = free_report
            st.session_state.comparison_openai_report = openai_report
            st.session_state.comparison_engine = engine_name
            st.session_state.comparison_rows = comparison_rows
            st.success(
                "Both live reports are complete. One paid OpenAI API call was used."
            )
        except ValueError as error:
            st.error(str(error))
        except Exception:
            st.error(
                "The live comparison could not be completed. Check the terminal "
                "for connection or model errors, then try again."
            )


if (
    st.session_state.comparison_free_report
    and st.session_state.comparison_openai_report
    and st.session_state.comparison_rows
):
    st.divider()
    st.subheader("Requirement-level comparison")

    if st.session_state.comparison_engine == "lexical fallback":
        st.warning(
            "The embedding model was unavailable, so the free report used the "
            "simpler keyword fallback."
        )

    comparison_rows = st.session_state.comparison_rows
    agreements, comparable = agreement_summary(comparison_rows)
    disagreements = comparable - agreements

    metric_left, metric_right = st.columns(2)
    metric_left.metric("Same assessment", f"{agreements}/{comparable}")
    metric_right.metric("Different assessment", str(disagreements))

    st.dataframe(
        [
            {
                "Requirement": row.requirement,
                "Free": row.free_assessment,
                "OpenAI": row.openai_assessment,
                "Agreement": "Yes" if row.agrees else "No",
            }
            for row in comparison_rows
        ],
        hide_index=True,
        width="stretch",
    )
    st.info(
        "Agreement measures whether the two reports use the same assessment. "
        "It does not prove that either assessment is correct. Use human-labeled "
        "expected results when measuring accuracy."
    )

    st.subheader("Full live reports")
    free_column, openai_column = st.columns(2)

    with free_column:
        st.markdown("### Free semantic report")
        st.caption(f"Engine: {st.session_state.comparison_engine}")
        render_downloads(
            st.session_state.comparison_free_report,
            "live_free_job_match_report",
        )
        with st.container(border=True):
            st.markdown(st.session_state.comparison_free_report)

    with openai_column:
        st.markdown("### Live OpenAI report")
        st.caption("One paid API response generated for this comparison")
        render_downloads(
            st.session_state.comparison_openai_report,
            "live_openai_job_match_report",
        )
        with st.container(border=True):
            st.markdown(st.session_state.comparison_openai_report)
