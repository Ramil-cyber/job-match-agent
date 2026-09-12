import asyncio
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from pdf_utils import create_job_match_pdf
from public_analysis import (
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
from public_openai import PublicInputRejectedError, run_public_openai_analysis
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

    st.subheader("Live OpenAI job-match analysis")
    st.caption(
        "Sign-in and persistent limits protect this portfolio demo from "
        "unmetered API use."
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

    st.metric(
        "Your remaining analyses",
        f"{current_quota.user_remaining}/{config.user_limit}",
    )

    if not current_quota.allowed:
        st.warning(quota_denial_message(current_quota))
        render_live_session_report()
        return

    st.info(
        "Privacy: Use fictional or redacted information. Submitted text is sent "
        "to OpenAI for this analysis and is not saved by this app."
    )
    st.caption(
        "Each submitted analysis reserves one account attempt before any API "
        "request. The attempt remains counted if processing later fails."
    )

    with st.form("public_openai_job_match_form"):
        resume_text = st.text_area(
            "Resume",
            height=250,
            max_chars=config.max_resume_characters,
            placeholder="Paste a fictional or redacted resume here.",
        )
        job_description_text = st.text_area(
            "Job Description",
            height=250,
            max_chars=config.max_job_characters,
            placeholder="Paste the job description here.",
        )
        privacy_confirmed = st.checkbox(
            "I confirm that I removed sensitive personal information and "
            "understand that the submitted text will be sent to OpenAI."
        )
        submitted = st.form_submit_button(
            "Analyze Match",
            type="primary",
            width="stretch",
        )

    if submitted:
        validation_message = validate_public_inputs(
            resume=resume_text,
            job_description=job_description_text,
            config=config,
        )

        if validation_message:
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
    page_icon="📄",
    layout="centered",
)

sample_resume, sample_job, sample_report = load_sample_files()

st.title("Job Match Agent")
st.write(
    "Explore an OpenAI-powered, evidence-based resume and job-description "
    "matching system through a saved fictional example and a protected live "
    "workflow."
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
- **Limited public agent:** Requires verified sign-in and enforces persistent
  per-account, daily, and overall usage limits before any paid request.
- **Saved example:** Displays a validated, pre-generated OpenAI report without
  sign-in or an API call.
- **Guardrails:** Uses only resume evidence, separates matches from gaps, rejects
  incomplete reports, constrains input and output size, performs safety screening,
  and supports PDF and Markdown downloads.
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
    st.link_button(
        "Report an application issue",
        "https://github.com/Ramil-cyber/job-match-agent/issues/new",
        icon=":material/bug_report:",
        width="stretch",
    )
    st.caption(
        "Do not include resumes, personal information, credentials, or secrets "
        "in a GitHub issue."
    )
