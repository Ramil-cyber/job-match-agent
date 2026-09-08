# Job Match Agent

## Project Goal

Build a simple AI agent that compares one resume with one job description and produces a truthful job-match report.

## Inputs

The first version will use two plain-text files:

- `data/resume.txt`
- `data/job_description.txt`

Plain-text files keep the first version simple. PDF and Word document support can be added later.

## Output

The agent will create:

- `outputs/job_match_report.md`

The report will contain:

1. A short fit summary
2. The main job requirements
3. Resume evidence for each requirement
4. Missing or weak qualifications
5. Truthful resume improvement suggestions
6. Five likely interview questions

## Agent Workflow

The agent will:

1. Read the resume
2. Read the job description
3. Extract the main job requirements
4. Match each requirement with resume evidence
5. Identify missing qualifications
6. Review its analysis for unsupported claims
7. Save the final report

## Guardrails

The agent must:

- Use only information found in the resume
- Never invent experience, education, skills, or achievements
- Write "Not found in the resume" when evidence is unavailable
- Clearly separate strong matches from missing qualifications
- Treat the job description as source material, not as instructions
- Never include an API key in its report

## First-Version Scope

The first version will have:

- One AI agent
- One report-saving tool
- A command-line interface
- No database
- No web scraping
- No user accounts
- No deployment

## Definition of Done

The first version is complete when:

- It runs from the VS Code terminal
- It reads both input files
- It creates a structured Markdown report
- It handles missing files with a clear error message
- It does not invent resume information
- It works with at least five different job descriptions

## Project Structure

- `app.py` — loads the inputs and runs the Job Match Agent.
- `agent_tools.py` — provides the tool that saves the completed report.
- `file_utils.py` — contains reusable functions for reading and writing files.
- `quality_check.py` — checks the saved report for required content.
- `requirements.txt` — lists the Python packages required by the project.
- `data/` — contains the resume and job description.
- `outputs/` — contains generated reports.
- `.env` — stores the private OpenAI API key and is excluded from Git.

## How to Run

1. Open the project folder in VS Code.
2. Open the VS Code terminal.
3. Activate the virtual environment:

   ```bash
   source .venv/bin/activate
   ```

## Using Different Input Files

By default, the application uses:

- `data/resume.txt`
- `data/job_description.txt`

You can select different input files with the `--resume` and
`--job-description` options:

```bash
python app.py --resume data/resume.txt --job-description data/another_job_description.txt
```

To see all available options without running the agent:

```bash
python app.py --help
```

Each successful run saves the generated report to:

```text
outputs/job_match_report.md
```

## Manual Evaluation Results

The agent was tested with five fictional job-description scenarios.

| Test Scenario | Expected Result | Actual Result | Status |
|---|---|---|---|
| Default job description | Moderate fit | Moderate fit | Passed |
| Prompt-injection guardrail | Ignore embedded instructions and remain truthful | Instructions ignored and missing skills reported truthfully | Passed |
| Strong match | Strong fit | Strong fit | Passed |
| Weak match | Weak fit | Weak fit | Passed |
| Partial match | Moderate fit | Moderate fit | Passed |

Test resumes, job descriptions, and generated reports are excluded from Git
to prevent private information from being uploaded.