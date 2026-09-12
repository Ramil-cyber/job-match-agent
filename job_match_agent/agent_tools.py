from agents import function_tool

from .file_utils import PROJECT_ROOT, save_text_file

# Define the only location where the agent can save its report.
REPORT_PATH = PROJECT_ROOT / "outputs" / "job_match_report.md"


@function_tool
def save_job_match_report(report_content: str) -> str:
    """Save the complete Markdown job-match report to the output file."""

    saved_path = save_text_file(
        file_path=REPORT_PATH,
        content=report_content,
    )

    return f"Report saved successfully to {saved_path}"
