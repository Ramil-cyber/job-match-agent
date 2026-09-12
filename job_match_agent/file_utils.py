from pathlib import Path

# Identify the main project folder above this package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_text_file(file_path: Path) -> str:
    """Read a text file and return its content."""

    if not file_path.is_file():
        raise FileNotFoundError(f"Required file was not found: {file_path}")

    content = file_path.read_text(encoding="utf-8").strip()

    if not content:
        raise ValueError(f"Required file is empty: {file_path}")

    return content


def save_text_file(file_path: Path, content: str) -> Path:
    """Save text to a file and return the file's path."""

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

    return file_path


# Test the functions when this file is run directly.
if __name__ == "__main__":
    resume_path = PROJECT_ROOT / "data" / "resume.txt"
    job_description_path = PROJECT_ROOT / "data" / "job_description.txt"

    resume = read_text_file(resume_path)
    job_description = read_text_file(job_description_path)

    print(f"Resume loaded: {len(resume)} characters")
    print(f"Job description loaded: {len(job_description)} characters")

    test_output_path = PROJECT_ROOT / "outputs" / "save_test.txt"

    saved_path = save_text_file(
        file_path=test_output_path,
        content="File-saving function works.",
    )

    print(f"Test file saved: {saved_path}")
