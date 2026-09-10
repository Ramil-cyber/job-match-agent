# Job Match Agent

## Project Overview

Job Match Agent compares a resume with a job description and produces a
structured, evidence-based match report.

## Live Public Demo

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://ramil-job-match-demo.streamlit.app/)

Try the cost-safe public portfolio app at
[ramil-job-match-demo.streamlit.app](https://ramil-job-match-demo.streamlit.app/).
It accepts custom resume and job-description text without making paid OpenAI
API calls. Use fictional or redacted information in public demonstrations.

The project uses a hybrid portfolio architecture:

- A public, cost-safe Streamlit demo uses local semantic embeddings and explicit
  skill checks. It accepts custom text without making paid OpenAI API calls.
- A pre-generated fictional OpenAI report demonstrates the private agent's
  richer analysis without creating a new API charge.
- A separate private Streamlit app and command-line application use OpenAI for
  deeper reasoning.
- A local-only comparison app runs both modes on the same input and displays
  their live reports side by side.
- A transparent benchmark compares both modes with human-labeled expected results.

## Features

Both analysis modes:

1. Identify required and preferred job qualifications.
2. Match each requirement with evidence from the resume.
3. Clearly identify missing or weak qualifications.
4. Suggest truthful resume improvements.
5. Generate five likely interview questions.
6. Validate the report before displaying or downloading it.
7. Provide PDF and Markdown downloads.

## Analysis Modes

### Public semantic demo

`portfolio_app.py` uses the open-source `BAAI/bge-small-en-v1.5` embedding model
through FastEmbed. It combines semantic similarity with explicit checks for named
skills, education, and years of experience.

This mode:

- Makes no OpenAI API call
- Has no per-analysis OpenAI cost
- Accepts custom resume and job-description text
- Includes a deterministic keyword fallback if the embedding model is unavailable
- Produces a more predictable, templated report

### Private OpenAI agent

`web_app.py` provides the full OpenAI-powered Streamlit experience. `app.py`
provides the command-line version. These modes require an OpenAI API key and each
successful analysis makes a paid API request.

The public portfolio app also includes a saved fictional OpenAI report that can
be viewed and downloaded without making a new API call.

### Local live comparison

`local_comparison_app.py` runs both modes with exactly the same resume and job
description. It aligns their requirement assessments, shows agreements and
differences, and displays both complete reports side by side. Opening the app
costs nothing; each selection of **Compare Both** makes one paid OpenAI API call.

This entry point is protected by a separate local environment flag and must not
be deployed publicly with an API key.

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
- Never include an API key in a report
- Require human review rather than make automated hiring decisions

## Project Structure

- `portfolio_app.py` - provides the public, cost-safe Streamlit demo.
- `semantic_analyzer.py` - extracts and matches requirements without a paid API.
- `quality_benchmark.py` - reproduces the no-cost comparison with the saved OpenAI report.
- `BENCHMARK.md` - documents the benchmark method, results, and limitations.
- `local_comparison_app.py` - runs both analyzers side by side for private local testing.
- `comparison_utils.py` - aligns report requirements and calculates model agreement.
- `web_app.py` - provides the private OpenAI-powered Streamlit app.
- `app.py` - runs the OpenAI-powered command-line application.
- `agent_core.py` - contains the shared OpenAI agent configuration.
- `agent_tools.py` - saves command-line reports.
- `file_utils.py` - reads and writes project files.
- `pdf_utils.py` - converts reports into formatted PDF data.
- `report_validation.py` - validates report structure and completeness.
- `quality_check.py` - checks the command-line report.
- `tests/` - contains automated analyzer, validator, and PDF tests.
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

Start the cost-safe public demo:

```bash
python -m streamlit run portfolio_app.py
```

Open the local address shown in the terminal, normally:

```text
http://localhost:8501
```

The first analysis may take longer while FastEmbed downloads the fixed embedding
model. It does not require an OpenAI API key or make paid OpenAI API calls.

The portfolio app contains four sections:

- **Try Free Analysis** - run the semantic analyzer with custom text.
- **View OpenAI Example** - inspect a saved fictional OpenAI report.
- **Quality Comparison** - review the labeled sample benchmark.
- **How It Works** - understand the architecture, safeguards, and limitations.

## Run the Private OpenAI App

Create the local environment file:

```bash
cp .env.example .env
```

Add your OpenAI API key to `.env`:

```text
OPENAI_API_KEY=your_real_api_key_here
```

Never commit or share the `.env` file.

Start the private app:

```bash
python -m streamlit run web_app.py
```

Paste a resume and job description, then select **Analyze Match**. Opening the
page does not call OpenAI, but each successful analysis creates one API run.

## Run the Local Live Comparison

The comparison app uses the local `.env` file. Enable its additional safety gate:

```text
ENABLE_PAID_LOCAL_COMPARISON=true
```

Then start it:

```bash
python -m streamlit run local_comparison_app.py
```

Select **Load fictional example** or paste custom text. Each selection of
**Compare Both** creates one paid OpenAI API call and one free semantic analysis.
The resulting agreement metric shows consistency between the two reports, not
ground-truth accuracy.

Keep `ENABLE_PAID_LOCAL_COMPARISON=false` when the comparison app is not being
used. Never deploy this entry point publicly with an OpenAI API key.

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

## Reproduce the Quality Benchmark

Run:

```bash
python quality_benchmark.py
```

The benchmark makes no OpenAI API call. It compares a newly generated semantic
report and the saved OpenAI example with eight human-labeled expected assessments.

In the current fictional sample, both modes matched 8 of 8 expected labels and
made zero false-positive qualification claims. This is a one-scenario smoke test,
not a general 100% accuracy claim. See [`BENCHMARK.md`](BENCHMARK.md) for details.

## Run Automated Tests

Run all tests:

```bash
python -m unittest discover -s tests -v
```

The 16 tests confirm that:

- Complete reports pass validation
- Incomplete or incorrectly structured reports are rejected
- The semantic analyzer extracts and matches expected qualifications
- Live report tables can be aligned even when requirements are paraphrased or reordered
- Missing or additional report rows are clearly identified
- Prompt-injection text is excluded from extracted requirements
- The keyword fallback produces a structurally valid report
- PDF generation returns valid PDF data
- Empty analyzer and PDF inputs are rejected

## Privacy and Cost

The public portfolio app processes submitted text in memory on the Streamlit app
server. The application does not write that text to a file or database and does
not send it to OpenAI. Because processing occurs on a hosted server rather than
the visitor's device, users should still submit fictional or redacted information.

The private web app and command-line application send resume and job-description
text to the OpenAI API. The command-line version saves its completed report in
`outputs/`. The private web app creates downloads in the active session.

The `.env`, `data/`, and `outputs/` paths are excluded from Git.

## Current Limitations

- The project analyzes one resume and one job description at a time.
- The web interfaces accept pasted text rather than directly parsing PDF or Word files.
- The public analyzer can miss nuance, negation, or uncommon terminology.
- The benchmark currently contains one labeled fictional scenario.
- Live model agreement does not identify which model is correct without human labels.
- The project does not use a database or provide user accounts.
- All results require human verification and must not be used as automated hiring decisions.

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
