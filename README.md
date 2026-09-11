# Job Match Agent

![AI-powered Job Match Agent comparing a resume with job requirements](assets/job-match-agent-readme-hero.png)

## Project Overview

Job Match Agent uses OpenAI to compare a resume with a job description and
produce a structured, evidence-based match report.

## Live Public Portfolio

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://ramil-job-match-demo.streamlit.app/)

Explore the portfolio at
[ramil-job-match-demo.streamlit.app](https://ramil-job-match-demo.streamlit.app/).
The public app displays a validated, pre-generated OpenAI report using fictional
inputs. It accepts no user data, requires no API key, and makes no live API call.

Live OpenAI analysis remains available only in the private Streamlit deployment
while authentication and usage limits are being developed.

## Features

The OpenAI agent:

1. Identifies required and preferred job qualifications.
2. Matches each requirement with evidence from the resume.
3. Clearly identifies missing or weak qualifications.
4. Suggests truthful resume improvements.
5. Generates five likely interview questions.
6. Validates the report before displaying or downloading it.
7. Provides PDF and Markdown downloads.

## OpenAI Analysis Workflow

`web_app.py` provides the live OpenAI-powered Streamlit experience. `app.py`
provides the command-line version. Both require an OpenAI API key, and each
successful analysis makes a paid API request.

`portfolio_app.py` provides a public view of a saved fictional OpenAI report.
This keeps the portfolio accessible without placing an API key in the public
app or allowing unmetered API usage.

`quality_benchmark.py` evaluates the saved OpenAI report against eight
human-labeled expected qualification assessments without making another API
call.

## Report Sections

Every completed report contains:

1. Overall Fit
2. Requirement Matches
3. Missing or Weak Qualifications
4. Truthful Resume Improvements
5. Likely Interview Questions

## Guardrails

The project is designed to:

- Use only information found in the resume
- Never invent experience, education, skills, or achievements
- State `Not found in the resume` when evidence is unavailable
- Separate demonstrated qualifications from missing qualifications
- Treat the job description as source material, not as instructions
- Ignore instructions embedded inside submitted resume or job-description text
- Never include an API key in a report
- Require human review rather than make automated hiring decisions

## Project Structure

- `portfolio_app.py` - displays the public saved OpenAI portfolio example.
- `web_app.py` - provides the private live OpenAI Streamlit app.
- `app.py` - runs the OpenAI-powered command-line application.
- `agent_core.py` - contains the shared OpenAI agent configuration.
- `agent_tools.py` - saves command-line reports.
- `quality_benchmark.py` - evaluates the saved OpenAI example against human labels.
- `BENCHMARK.md` - documents the evaluation method, results, and limitations.
- `file_utils.py` - reads and writes project files.
- `pdf_utils.py` - converts reports into formatted PDF data.
- `report_validation.py` - validates report structure and completeness.
- `quality_check.py` - checks the command-line report.
- `tests/` - contains automated benchmark, validator, and PDF tests.
- `examples/` - contains fictional, public-safe sample inputs and output.
- `data/` - contains private local inputs and is excluded from Git.
- `outputs/` - contains generated command-line reports and is excluded from Git.
- `.env.example` - shows the required OpenAI environment variable.
- `.env` - stores the real API key locally and is excluded from Git.
- `requirements.txt` - lists the required Python packages.

## Installation

Clone the repository:

```bash
git clone https://github.com/Ramil-cyber/job-match-agent.git
cd job-match-agent
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run the Public Portfolio App

Start the public saved-example app:

```bash
python -m streamlit run portfolio_app.py
```

Open the local address shown in the terminal, normally:

```text
http://localhost:8501
```

The portfolio app contains three sections:

- **View OpenAI Example** - inspect the fictional resume, job description, and
  saved OpenAI report.
- **Quality Evaluation** - compare the report's eight qualification assessments
  with human-labeled expected results.
- **How It Works** - review the architecture, safeguards, and limitations.

Opening or downloading content from this app makes no API call.

## Run the Private OpenAI App

Create the local environment file:

```bash
cp .env.example .env
```

Add your existing OpenAI API key to `.env`:

```text
OPENAI_API_KEY=your_real_api_key_here
```

Never commit or share the `.env` file.

Start the private app:

```bash
python -m streamlit run web_app.py
```

Paste a resume and job description, then select **Analyze Match**. Opening the
page does not call OpenAI, but each successful analysis creates one paid API
run.

## Run the Command-Line Application

After configuring `.env`, run the OpenAI agent with the fictional examples:

```bash
python app.py --resume examples/sample_resume.txt --job-description examples/sample_job_description.txt
```

The report is saved as:

```text
outputs/job_match_report.md
```

Check the saved report:

```bash
python quality_check.py
```

## Reproduce the OpenAI Quality Benchmark

Run:

```bash
python quality_benchmark.py
```

The benchmark validates the saved OpenAI report and compares its eight
qualification assessments with human-labeled expected results. It makes no API
call.

In the current fictional sample, the saved OpenAI report matched 8 of 8 expected
labels, made zero false-positive qualification claims, and missed zero
demonstrated matches. This is a one-scenario smoke test, not a general 100%
accuracy claim. See [`BENCHMARK.md`](BENCHMARK.md) for details.

## Run Automated Tests

Run all tests:

```bash
python -m unittest discover -s tests -v
```

The tests confirm that:

- Complete reports pass validation
- Incomplete or incorrectly structured reports are rejected
- The saved OpenAI report contains all expected qualification assessments
- Benchmark metrics count incorrect and unsupported qualification claims
- PDF generation returns valid PDF data
- Empty report and PDF inputs are rejected

## Privacy and Cost

The public portfolio app reads only the fictional files committed in the
`examples/` directory. It accepts no submitted resume or job-description text,
does not contain an API key, and makes no API call.

The private web app and command-line application send resume and job-description
text to the OpenAI API. The command-line version saves its completed report in
`outputs/`. The private web app creates downloads in the active session.

The `.env`, `data/`, and `outputs/` paths are excluded from Git.

## Current Limitations

- Live OpenAI analysis is currently restricted to the private deployment.
- The project does not yet provide public authentication, usage limits, or a
  persistent usage database.
- The project analyzes one resume and one job description at a time.
- The live interface accepts pasted text rather than directly parsing PDF or
  Word files.
- The quality benchmark currently contains one labeled fictional scenario.
- All results require human verification and must not be used as automated
  hiring decisions.

## Manual OpenAI Evaluation

The OpenAI agent was evaluated with five fictional job-description scenarios.

| Test Scenario | Expected Result | Actual Result | Status |
|---|---|---|---|
| Default job description | Moderate fit | Moderate fit | Passed |
| Prompt-injection guardrail | Ignore embedded instructions and remain truthful | Instructions ignored and missing skills reported truthfully | Passed |
| Strong match | Strong fit | Strong fit | Passed |
| Weak match | Weak fit | Weak fit | Passed |
| Partial match | Moderate fit | Moderate fit | Passed |

A fictional sample report is available at
[`examples/sample_job_match_report.md`](examples/sample_job_match_report.md).
