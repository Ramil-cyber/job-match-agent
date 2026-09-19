import asyncio
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from job_match_agent.pdf_utils import create_job_match_pdf
from job_match_agent.public_analysis import (
    PublicAnalysisConfig,
    PublicAnalysisConfigurationError,
    QuotaDecision,
    QuotaServiceError,
    SupabaseQuotaClient,
    auth_settings_are_valid,
    build_private_user_key,
    build_safety_identifier,
    load_public_analysis_config,
    validate_public_inputs,
)
from job_match_agent.public_openai import (
    PublicInputRejectedError,
    run_public_openai_analysis,
)
from job_match_agent.quality_benchmark import (
    EXPECTED_ASSESSMENTS,
    calculate_metrics,
    extract_assessments,
)
from job_match_agent.report_validation import validate_job_match_report
from job_match_agent.streamlit_inputs import render_document_input
from job_match_agent.streamlit_ui import (
    apply_shared_styles,
    render_feature_grid,
    render_footer,
    render_hero,
    render_section_header,
    render_workflow_steps,
)

PROJECT_ROOT = Path(__file__).resolve().parent
SAMPLE_RESUME_PATH = PROJECT_ROOT / "examples" / "sample_resume.txt"
SAMPLE_JOB_PATH = PROJECT_ROOT / "examples" / "sample_job_description.txt"
SAMPLE_REPORT_PATH = PROJECT_ROOT / "examples" / "sample_job_match_report.md"
# Root-level Streamlit secrets are exposed as environment variables in the
# deployed app. Locally, load the same settings from the ignored .env file.
load_dotenv()


try:
    public_analysis_config = load_public_analysis_config()
except PublicAnalysisConfigurationError:
    public_analysis_config = None


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
    st.markdown("#### Export report")
    st.caption("Keep a portable copy for review, notes, or interview preparation.")
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


def render_live_session_report() -> None:
    """Display the current verified user's session-only live report."""

    if not st.session_state.get("public_job_match_report"):
        return

    report_markdown = st.session_state.public_job_match_report
    st.divider()
    render_section_header(
        eyebrow="Your result",
        title="Analysis complete",
        description=(
            "Review the evidence, gaps, and recommendations before exporting "
            "or using any suggestion."
        ),
    )
    with st.container(border=True):
        st.markdown(report_markdown)
    render_report_downloads(report_markdown, "public_openai_job_match_report")
    st.caption(
        "AI-generated guidance. Verify every result before using it in a "
        "job application."
    )


def auth_is_configured() -> bool:
    """Return whether the required Streamlit OIDC settings are present."""

    try:
        auth_settings = st.secrets["auth"]
    except (FileNotFoundError, KeyError):
        return False

    return auth_settings_are_valid(auth_settings)


def quota_denial_message(decision: QuotaDecision) -> str:
    """Return a user-facing message without revealing internal counters."""

    if decision.denial_reason == "user_limit":
        return (
            "You have used all public OpenAI analysis attempts available to "
            "this account."
        )
    if decision.denial_reason == "daily_limit":
        return (
            "The public demo has reached today's shared analysis limit. "
            "Please try again tomorrow."
        )
    if decision.denial_reason == "total_limit":
        return (
            "The public demo has reached its overall analysis allowance and "
            "is temporarily unavailable."
        )

    return "Live analysis is temporarily unavailable."


def render_live_analysis(config: PublicAnalysisConfig | None) -> None:
    """Render the fail-closed, authenticated public OpenAI workflow."""

    render_section_header(
        eyebrow="Protected live workflow",
        title="Analyze a resume against a role",
        description=(
            "Sign in, add two documents, and receive an evidence-based report. "
            "Persistent limits protect the public demo from unmetered API use."
        ),
    )

    if config is None:
        st.error("Live analysis is unavailable because its settings are invalid.")
        return

    if not config.enabled:
        st.info(
            "Live analysis is currently disabled. You can still explore the "
            "saved fictional OpenAI example."
        )
        return

    if not config.is_ready or not auth_is_configured():
        st.error("Live analysis is not fully configured and remains safely disabled.")
        return

    if not st.user.is_logged_in:
        st.info(
            "Sign in with Google to use the limited live analysis. Viewing the "
            "saved fictional example does not require sign-in."
        )
        st.button(
            "Sign in with Google",
            on_click=st.login,
            type="primary",
            width="stretch",
        )
        return

    issuer = str(getattr(st.user, "iss", "")).strip()
    subject = str(getattr(st.user, "sub", "")).strip()
    email_verified = getattr(st.user, "email_verified", False)

    if not issuer or not subject or email_verified not in (True, "true", "True"):
        st.error("The signed-in account could not be verified.")
        st.button("Sign out", on_click=st.logout, width="stretch")
        return

    user_key = build_private_user_key(
        issuer=issuer,
        subject=subject,
        salt=config.user_hash_salt,
    )

    if st.session_state.get("public_report_user") != user_key:
        st.session_state.public_job_match_report = None
        st.session_state.public_report_user = user_key

    account_column, logout_column = st.columns([3, 1])
    display_name = str(getattr(st.user, "name", "Signed-in user")).strip()
    account_column.text(f"Signed in as {display_name or 'Verified user'}")
    logout_column.button(
        "Sign out",
        on_click=st.logout,
        width="stretch",
    )

    try:
        quota_client = SupabaseQuotaClient(
            supabase_url=config.supabase_url,
            secret_key=config.supabase_secret_key,
        )
        current_quota = quota_client.read_quota(
            user_key=user_key,
            config=config,
        )
    except (PublicAnalysisConfigurationError, QuotaServiceError):
        st.error(
            "The usage-limit service is temporarily unavailable. No OpenAI "
            "request was made."
        )
        render_live_session_report()
        return

    remaining_column, limit_column, format_column = st.columns(3)
    remaining_column.metric(
        "Analyses remaining",
        f"{current_quota.user_remaining}/{config.user_limit}",
    )
    limit_column.metric("Per-account allowance", config.user_limit)
    format_column.metric("Accepted formats", "PDF · DOCX · TXT")

    render_workflow_steps(
        (
            ("Add your resume", "Paste text or upload a readable document."),
            ("Add the role", "Provide the complete job description."),
            ("Review the report", "Check every claim before using it."),
        )
    )

    if not current_quota.allowed:
        st.warning(quota_denial_message(current_quota))
        render_live_session_report()
        return

    st.info(
        "Privacy: Use fictional or redacted information. Pasted text and text "
        "extracted from uploads are sent to OpenAI for this analysis and are "
        "not saved by this app."
    )
    st.caption(
        "Each submitted analysis reserves one account attempt before any API "
        "request. The attempt remains counted if processing later fails."
    )

    resume_column, job_column = st.columns(2, gap="large")

    with resume_column, st.container(border=True):
        st.markdown("#### 1 · Resume")
        st.caption("Use fictional or carefully redacted information.")
        resume_input = render_document_input(
            "Resume",
            key_prefix="public_resume",
            max_characters=config.max_resume_characters,
            paste_placeholder="Paste a resume here.",
        )

    with job_column, st.container(border=True):
        st.markdown("#### 2 · Job description")
        st.caption("Include required and preferred qualifications.")
        job_description_input = render_document_input(
            "Job Description",
            key_prefix="public_job_description",
            max_characters=config.max_job_characters,
            paste_placeholder="Paste the job description here.",
        )

    with st.container(border=True):
        st.markdown("#### 3 · Review and analyze")
        privacy_confirmed = st.checkbox(
            "I confirm that I removed sensitive personal information and "
            "understand that pasted text or uploaded document content will be "
            "sent to OpenAI."
        )
        submitted = st.button(
            "Analyze job match",
            type="primary",
            width="stretch",
            key="public_analyze_match",
            icon=":material/auto_awesome:",
        )

    if submitted:
        resume_text = resume_input.text
        job_description_text = job_description_input.text
        validation_message = validate_public_inputs(
            resume=resume_text,
            job_description=job_description_text,
            config=config,
        )

        if resume_input.error or job_description_input.error:
            st.error("Resolve the document upload error before analyzing.")
        elif validation_message:
            st.error(validation_message)
        elif not privacy_confirmed:
            st.error("Please confirm the privacy notice before continuing.")
        else:
            st.session_state.public_job_match_report = None

            try:
                reservation = quota_client.reserve_attempt(
                    user_key=user_key,
                    config=config,
                )
            except QuotaServiceError:
                st.error(
                    "The usage-limit service is temporarily unavailable. "
                    "No OpenAI request was made."
                )
            else:
                if not reservation.allowed:
                    st.warning(quota_denial_message(reservation))
                else:
                    try:
                        with st.spinner(
                            "Analyzing the match...",
                            show_time=True,
                        ):
                            report = asyncio.run(
                                run_public_openai_analysis(
                                    resume=resume_text.strip(),
                                    job_description=job_description_text.strip(),
                                    config=config,
                                    safety_identifier=build_safety_identifier(user_key),
                                )
                            )

                        st.session_state.public_job_match_report = report
                        st.success(
                            "Analysis complete. "
                            f"{reservation.user_remaining} account attempt(s) "
                            "remain."
                        )
                    except PublicInputRejectedError:
                        st.error(
                            "The submitted text could not be processed by this "
                            "public demo. This attempt was counted."
                        )
                    # Convert provider, network, and validation failures into a
                    # generic message so no internal or secret details leak.
                    except Exception:  # noqa: BLE001
                        st.error(
                            "The analysis could not be completed. This attempt "
                            "was counted to keep the public cost limit reliable."
                        )

    render_live_session_report()


st.set_page_config(
    page_title="Job Match Agent Portfolio",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "About": (
            "Job Match Agent is an evidence-based OpenAI portfolio project. "
            "It is not an automated hiring decision system."
        )
    },
)

apply_shared_styles()

sample_resume, sample_job, sample_report = load_sample_files()

render_hero(
    eyebrow="AI-powered career intelligence",
    title="Match your experience.",
    highlighted_title="Plan your next move.",
    description=(
        "Compare resume evidence with role requirements, uncover gaps, and "
        "turn the result into practical preparation—without overstating your "
        "background."
    ),
    badges=(
        "Evidence-first matching",
        "Protected live demo",
        "PDF · DOCX · TXT",
    ),
)
if public_analysis_config and public_analysis_config.enabled:
    st.info(
        "Signed-in users can run limited live OpenAI analysis. The saved "
        "fictional example remains available without sign-in or an API call."
    )
else:
    st.info(
        "The saved fictional OpenAI example is available without an API call. "
        "Live public analysis remains safely disabled until its protections "
        "are configured and tested."
    )

if public_analysis_config is None or public_analysis_config.enabled:
    live_tab, report_tab, evaluation_tab, about_tab = st.tabs(
        [
            "Live OpenAI Analysis",
            "View OpenAI Example",
            "Quality Evaluation",
            "How It Works",
        ]
    )

    with live_tab:
        render_live_analysis(public_analysis_config)
else:
    report_tab, evaluation_tab, about_tab = st.tabs(
        [
            "View OpenAI Example",
            "Quality Evaluation",
            "How It Works",
        ]
    )


with report_tab:
    render_section_header(
        eyebrow="No sign-in · No API call",
        title="Explore a complete fictional example",
        description=(
            "See exactly how the agent connects each requirement to resume "
            "evidence before trying the protected live workflow."
        ),
    )

    source_column, requirement_column, api_column = st.columns(3)
    source_column.metric("Report source", "Saved OpenAI output")
    requirement_column.metric("Requirements evaluated", "8")
    api_column.metric("API calls to view", "0")

    with st.expander("View the fictional sample inputs"):
        st.markdown("#### Resume")
        st.code(sample_resume, language=None)
        st.markdown("#### Job description")
        st.code(sample_job, language=None)

    with st.container(border=True):
        st.markdown(sample_report)
    render_report_downloads(sample_report, "sample_openai_job_match_report")
    st.caption(
        "AI-generated guidance. Verify every result before using it in a job "
        "application."
    )


with evaluation_tab:
    render_section_header(
        eyebrow="Reproducible benchmark",
        title="Human-labeled quality evaluation",
        description=(
            "Compare the saved report with eight expected assessments. This "
            "check is local, transparent, and makes no API call."
        ),
    )
    st.info(
        "This reproducible smoke test compares the saved OpenAI report with "
        "eight human-labeled expected assessments. Opening this tab makes no "
        "API call."
    )

    openai_assessments = extract_assessments(sample_report)
    metrics = calculate_metrics(openai_assessments)
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

    st.markdown("#### Assessment details")
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

    st.warning(
        "This result covers one fictional scenario and is not a general 100% "
        "accuracy claim. Results for other resumes and job descriptions can differ."
    )


with about_tab:
    render_section_header(
        eyebrow="System overview",
        title="One analysis workflow, three ways to explore",
        description=(
            "The same evidence rules power the owner-only agent, the protected "
            "public experience, and the zero-cost saved demonstration."
        ),
    )
    render_feature_grid(
        (
            (
                "01",
                "Private live agent",
                "Owner-only OpenAI analysis with paste and document upload inputs.",
            ),
            (
                "02",
                "Protected public agent",
                "Verified sign-in and persistent quotas before every paid request.",
            ),
            (
                "03",
                "Saved example",
                "A validated fictional report available without sign-in or API use.",
            ),
        )
    )
    st.markdown(
        """
- **Private live agent:** Uses OpenAI for requirement matching, evidence-based
  reasoning, resume suggestions, and interview questions.
- **Limited public agent:** Requires verified sign-in and enforces persistent
  per-account, daily, and overall usage limits before any paid request.
- **Saved example:** Displays a validated, pre-generated OpenAI report without
  sign-in or an API call.
- **Guardrails:** Uses only resume evidence, separates matches from gaps, rejects
  incomplete reports, accepts pasted text or safe PDF/DOCX/TXT extraction,
  constrains input and output size, performs safety screening, and supports PDF
  and Markdown downloads.
        """
    )
    st.warning(
        "This project is a portfolio demonstration, not an automated hiring "
        "decision system. Results require human review."
    )
    source_column, issue_column = st.columns(2)
    source_column.link_button(
        "View source code on GitHub",
        "https://github.com/Ramil-cyber/job-match-agent",
        icon=":material/code:",
        width="stretch",
    )
    issue_column.link_button(
        "Report an application issue",
        "https://github.com/Ramil-cyber/job-match-agent/issues/new",
        icon=":material/bug_report:",
        width="stretch",
    )
    st.caption(
        "Do not include resumes, personal information, credentials, or secrets "
        "in a GitHub issue."
    )


render_footer()
