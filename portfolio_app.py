from pathlib import Path

import streamlit as st
from fastembed import TextEmbedding

from pdf_utils import create_job_match_pdf
from report_validation import validate_job_match_report
from semantic_analyzer import create_semantic_job_match_report

MAX_INPUT_CHARACTERS = 10_000
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
PROJECT_ROOT = Path(__file__).resolve().parent
SAMPLE_RESUME_PATH = PROJECT_ROOT / "examples" / "sample_resume.txt"
SAMPLE_JOB_PATH = PROJECT_ROOT / "examples" / "sample_job_description.txt"
SAMPLE_REPORT_PATH = PROJECT_ROOT / "examples" / "sample_job_match_report.md"


@st.cache_resource(show_spinner=False)
def load_embedding_model() -> TextEmbedding:
    """Load one lightweight local model for all visitor sessions."""

    return TextEmbedding(model_name=EMBEDDING_MODEL_NAME)


@st.cache_data
def load_sample_files() -> tuple[str, str, str]:
    """Load and validate the fictional portfolio example."""

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
    page_title="Job Match Agent Portfolio Demo",
    page_icon="📄",
    layout="centered",
)

if "semantic_report" not in st.session_state:
    st.session_state.semantic_report = None

if "semantic_engine" not in st.session_state:
    st.session_state.semantic_engine = None


st.title("Job Match Agent")
st.write(
    "Explore a cost-safe portfolio version of an evidence-based "
    "resume and job-description matching system."
)

live_tab, sample_tab, benchmark_tab, about_tab = st.tabs(
    [
        "Try Free Analysis",
        "View OpenAI Example",
        "Quality Comparison",
        "How It Works",
    ]
)


with live_tab:
    st.subheader("Try the free local analysis")
    st.info(
        "This public mode uses a lightweight open-source embedding model on "
        "the app server. It does not use an OpenAI API key or make paid API calls."
    )
    st.caption(
        "Privacy: The application processes submitted text in memory and does "
        "not write it to a file or database. Use fictional or redacted information "
        "in any public demonstration."
    )

    with st.form("semantic_job_match_form"):
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
            "Run Free Analysis",
            type="primary",
            width="stretch",
        )

    if submitted:
        st.session_state.semantic_report = None
        st.session_state.semantic_engine = None

        if not resume_text.strip() or not job_description_text.strip():
            st.error("Please provide both a resume and a job description.")
        else:
            try:
                with st.spinner(
                    "Loading the local model and analyzing the match...",
                    show_time=True,
                ):
                    try:
                        embedding_model = load_embedding_model()
                    except Exception:
                        embedding_model = None

                    report, engine_name = create_semantic_job_match_report(
                        resume_text,
                        job_description_text,
                        embedding_model,
                    )
                    validated_report = validate_job_match_report(report)

                st.session_state.semantic_report = validated_report
                st.session_state.semantic_engine = engine_name
                st.success("Free analysis complete. No paid API was used.")
            except ValueError as error:
                st.error(str(error))
            except Exception:
                st.error(
                    "The local analysis could not be completed. "
                    "Please wait a moment and try again."
                )

    if st.session_state.semantic_report:
        st.divider()

        if st.session_state.semantic_engine == "lexical fallback":
            st.warning(
                "The embedding model was temporarily unavailable, so the app "
                "used its simpler keyword fallback."
            )

        st.markdown(st.session_state.semantic_report)
        render_report_downloads(
            st.session_state.semantic_report,
            "free_job_match_report",
        )
        st.caption(
            "Demonstration guidance only. Local semantic similarity can miss "
            "context, so verify every result before using it."
        )


with sample_tab:
    sample_resume, sample_job, sample_report = load_sample_files()

    st.subheader("Pre-generated OpenAI report")
    st.info(
        "This fictional example shows the richer report produced by the private "
        "OpenAI agent. Viewing or downloading it makes no API call."
    )

    with st.expander("View the fictional sample inputs"):
        st.markdown("#### Resume")
        st.code(sample_resume, language=None)
        st.markdown("#### Job description")
        st.code(sample_job, language=None)

    st.markdown(sample_report)
    render_report_downloads(sample_report, "sample_openai_job_match_report")


with benchmark_tab:
    st.subheader("Transparent quality comparison")
    st.info(
        "This no-cost benchmark compares the public analyzer and the saved "
        "OpenAI report with human-labeled expected results for one fictional "
        "resume and job description. Opening this tab makes no API call."
    )

    st.table(
        [
            {
                "Requirement": "Quantitative bachelor's degree",
                "Expected": "Meets",
                "Free": "Meets",
                "OpenAI": "Meets",
            },
            {
                "Requirement": "Two years of analytics experience",
                "Expected": "Meets",
                "Free": "Meets",
                "OpenAI": "Meets",
            },
            {
                "Requirement": "Python and SQL",
                "Expected": "Meets",
                "Free": "Meets",
                "OpenAI": "Meets",
            },
            {
                "Requirement": "Forecasting or machine learning",
                "Expected": "Meets",
                "Free": "Meets",
                "OpenAI": "Meets",
            },
            {
                "Requirement": "AWS",
                "Expected": "Missing",
                "Free": "Missing",
                "OpenAI": "Missing",
            },
            {
                "Requirement": "Written and verbal communication",
                "Expected": "Partial",
                "Free": "Partial",
                "OpenAI": "Partial",
            },
            {
                "Requirement": "Natural language processing",
                "Expected": "Missing",
                "Free": "Missing",
                "OpenAI": "Missing",
            },
            {
                "Requirement": "Executive dashboards",
                "Expected": "Partial",
                "Free": "Partial",
                "OpenAI": "Partial",
            },
        ]
    )

    free_metric, openai_metric = st.columns(2)
    free_metric.metric("Free classification", "8/8", "0 false claims")
    openai_metric.metric("Saved OpenAI classification", "8/8", "0 false claims")

    st.markdown(
        "The two modes agreed with every expected requirement label in this "
        "sample. The saved OpenAI report provides more tailored explanations, "
        "resume suggestions, and interview questions, while the public analyzer "
        "uses a more predictable template."
    )
    st.warning(
        "This is a smoke test using one fictional scenario, not a general 100% "
        "accuracy claim. Results for other resumes and job descriptions can differ."
    )


with about_tab:
    st.subheader("Two analysis modes, one tested workflow")
    st.markdown(
        """
- **Public demo:** Uses local semantic embeddings plus explicit skill checks. It
  accepts custom text and has no per-analysis API cost.
- **Private AI agent:** Uses OpenAI for deeper reasoning and natural-language
  reporting. Its API key is stored only in the private deployment.
- **Shared safeguards:** Both modes keep evidence separate from gaps, avoid
  inventing qualifications, validate report structure, and support PDF and
  Markdown downloads.
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
