import argparse
import asyncio
import os
from pathlib import Path

from agents import Runner
from dotenv import load_dotenv

from job_match_agent.agent_core import build_analysis_request, create_job_match_agent
from job_match_agent.file_utils import PROJECT_ROOT, read_text_file

# Load the API key from .env.
load_dotenv()


# Confirm that the API key is available.
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("OPENAI_API_KEY was not found in the .env file.")


# Define the default input-file locations.
RESUME_PATH = PROJECT_ROOT / "data" / "resume.txt"
JOB_DESCRIPTION_PATH = PROJECT_ROOT / "data" / "job_description.txt"


# Create the CLI version of the agent, which saves its report to a file.
job_match_agent = create_job_match_agent(save_to_file=True)


def parse_arguments() -> argparse.Namespace:
    """Read optional file paths provided in the terminal."""

    parser = argparse.ArgumentParser(
        description="Compare a resume with a job description."
    )

    parser.add_argument(
        "--resume",
        type=Path,
        default=RESUME_PATH,
        help="Path to the resume text file.",
    )

    parser.add_argument(
        "--job-description",
        type=Path,
        default=JOB_DESCRIPTION_PATH,
        help="Path to the job-description text file.",
    )

    return parser.parse_args()


def resolve_input_path(file_path: Path) -> Path:
    """Convert a relative input path into a full project path."""

    if file_path.is_absolute():
        return file_path

    return PROJECT_ROOT / file_path


async def main() -> None:
    """Load the selected files, run the agent, and display the result."""

    args = parse_arguments()

    resume_path = resolve_input_path(args.resume)
    job_description_path = resolve_input_path(args.job_description)

    try:
        resume = read_text_file(resume_path)
        job_description = read_text_file(job_description_path)

        analysis_request = build_analysis_request(
            resume=resume,
            job_description=job_description,
        )

        result = await Runner.run(
            job_match_agent,
            analysis_request,
        )

        print(result.final_output)

    except (FileNotFoundError, ValueError) as error:
        print(f"Input error: {error}")


if __name__ == "__main__":
    asyncio.run(main())
