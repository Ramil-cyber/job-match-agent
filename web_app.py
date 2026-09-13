import asyncio
import os

import streamlit as st
from agents import Runner
from dotenv import load_dotenv

from job_match_agent.agent_core import build_analysis_request, create_job_match_agent
from job_match_agent.pdf_utils import create_job_match_pdf
from job_match_agent.report_validation import validate_job_match_report
from job_match_agent.streamlit_inputs import render_document_input
from job_match_agent.streamlit_ui import (
    apply_shared_styles,
    render_footer,
    render_hero,
    render_section_header,
    render_workflow_steps,
)

MAX_INPUT_CHARACTERS = 10_000


# Load the local API key from .env.
load_dotenv()


# Create the web version of the agent without the file-saving tool.
web_agent = create_job_match_agent(save_to_file=False)


# Configure the browser page.
st.set_page_config(
    page_title="Job Match Agent",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "About": (
            "Private Job Match Agent workspace. Submitted content is sent to "
            "OpenAI and is not saved to a shared file."
        )
    },
)

apply_shared_styles()


# Keep the latest report available during the current browser session.
if "job_match_report" not in st.session_state:
    st.session_state.job_match_report = None


render_hero(
    eyebrow="Private analysis workspace",
    title="Turn role requirements into",
    highlighted_title="a focused plan.",
    description=(
        "Compare a resume with a job description and receive a structured "
        "report grounded only in the experience you provide."
    ),
    badges=(
        "Evidence-based report",
        "10,000 characters each",
        "PDF · DOCX · TXT",
    ),
)

st.info(
    "Privacy: Pasted text and text extracted from uploads are sent to the "
    "OpenAI API for analysis. This web version does not save uploads or input "
    "text to a shared file. Use fictional or redacted data."
)


render_section_header(
    eyebrow="Three-step workflow",
    title="Add your documents",
    description=(
        "Paste text directly or upload readable PDF, DOCX, and TXT files. "
        "Extracted content remains editable before analysis."
    ),
)

render_workflow_steps(
    (
        ("Add your resume", "Paste text or upload a readable document."),
        ("Add the role", "Provide the complete job description."),
        ("Review the report", "Verify every result before using it."),
    )
)

resume_column, job_column = st.columns(2, gap="large")

with resume_column, st.container(border=True):
    st.markdown("#### 1 · Resume")
    st.caption("Use fictional or carefully redacted information.")
    resume_input = render_document_input(
        "Resume",
        key_prefix="private_resume",
        max_characters=MAX_INPUT_CHARACTERS,
        paste_placeholder="Paste the resume text here.",
    )

with job_column, st.container(border=True):
    st.markdown("#### 2 · Job description")
    st.caption("Include required and preferred qualifications.")
    job_description_input = render_document_input(
        "Job Description",
        key_prefix="private_job_description",
        max_characters=MAX_INPUT_CHARACTERS,
        paste_placeholder="Paste the job description here.",
    )

with st.container(border=True):
    st.markdown("#### 3 · Analyze")
    st.caption("The report will appear below and remain available in this session.")
    submitted = st.button(
        "Analyze job match",
        type="primary",
        width="stretch",
        key="private_analyze_match",
        icon=":material/auto_awesome:",
    )


if submitted:
    st.session_state.job_match_report = None
    resume_text = resume_input.text
    job_description_text = job_description_input.text

    if resume_input.error or job_description_input.error:
        st.error("Resolve the document upload error before analyzing.")

    elif not resume_text.strip() or not job_description_text.strip():
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

        except Exception:  # noqa: BLE001
            st.error(
                "The analysis could not be completed. "
                "Please wait a moment and try again."
            )


if st.session_state.job_match_report:
    report_markdown = st.session_state.job_match_report
    pdf_report = create_job_match_pdf(report_markdown)

    st.divider()
    render_section_header(
        eyebrow="Your result",
        title="Analysis complete",
        description=(
            "Review the evidence, gaps, and suggestions before downloading or "
            "using any recommendation."
        ),
    )
    with st.container(border=True):
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
        "AI-generated guidance. Verify the report before using it in a job application."
    )


render_footer()
