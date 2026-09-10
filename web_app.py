import asyncio
import os

import streamlit as st
from agents import Runner
from dotenv import load_dotenv
from pdf_utils import create_job_match_pdf
from report_validation import validate_job_match_report

from agent_core import build_analysis_request, create_job_match_agent

MAX_INPUT_CHARACTERS = 10_000


# Load the local API key from .env.
load_dotenv()


# Create the web version of the agent without the file-saving tool.
web_agent = create_job_match_agent(save_to_file=False)


# Configure the browser page.
st.set_page_config(
    page_title="Job Match Agent",
    page_icon="📄",
    layout="centered",
)


# Keep the latest report available during the current browser session.
if "job_match_report" not in st.session_state:
    st.session_state.job_match_report = None


st.title("Job Match Agent")

st.write(
    "Compare your resume with a job description and receive a "
    "structured, evidence-based report."
)

st.info(
    "Privacy: Submitted text is sent to the OpenAI API for analysis. "
    "This web version does not save it to a shared report file. "
    "Use fictional data while the app is in development."
)


with st.form("job_match_form"):
    resume_text = st.text_area(
        "Resume",
        height=250,
        max_chars=MAX_INPUT_CHARACTERS,
        placeholder="Paste the resume text here.",
    )

    job_description_text = st.text_area(
        "Job Description",
        height=250,
        max_chars=MAX_INPUT_CHARACTERS,
        placeholder="Paste the job description here.",
    )

    submitted = st.form_submit_button(
        "Analyze Match",
        type="primary",
        width="stretch",
    )


if submitted:
    st.session_state.job_match_report = None

    if not resume_text.strip() or not job_description_text.strip():
        st.error("Please provide both a resume and a job description.")

    elif not os.getenv("OPENAI_API_KEY"):
        st.error(
            "The OpenAI API key is not configured. "
            "Add it securely before running an analysis."
        )

    else:
        analysis_request = build_analysis_request(
            resume=resume_text,
            job_description=job_description_text,
        )

        try:
            with st.spinner("Analyzing the match...", show_time=True):
                result = asyncio.run(
                    Runner.run(
                        web_agent,
                        analysis_request,
                    )
                )

            validated_report = validate_job_match_report(result.final_output)

            st.session_state.job_match_report = validated_report
            st.success("Analysis complete.")

        except Exception:
            st.error(
                "The analysis could not be completed. "
                "Please wait a moment and try again."
            )


if st.session_state.job_match_report:
    report_markdown = st.session_state.job_match_report
    pdf_report = create_job_match_pdf(report_markdown)

    st.divider()
    st.markdown(report_markdown)

    pdf_column, markdown_column = st.columns(2)

    with pdf_column:
        st.download_button(
            label="Download PDF",
            data=pdf_report,
            file_name="job_match_report.pdf",
            mime="application/pdf",
            on_click="ignore",
            icon=":material/picture_as_pdf:",
            width="stretch",
        )

    with markdown_column:
        st.download_button(
            label="Download Markdown",
            data=report_markdown + "\n",
            file_name="job_match_report.md",
            mime="text/markdown",
            on_click="ignore",
            icon=":material/download:",
            width="stretch",
        )

    st.caption(
        "AI-generated guidance. Verify the report before using it "
        "in a job application."
    )
