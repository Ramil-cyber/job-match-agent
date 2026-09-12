# Job Match Agent

![AI-powered Job Match Agent comparing a resume with job requirements](assets/job-match-agent-readme-hero.png)

## Project Overview

Job Match Agent uses OpenAI to compare a resume with a job description and
produce a structured, evidence-based match report.

## Live Public Portfolio

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://ramil-job-match-demo.streamlit.app/)

Explore the portfolio at
[ramil-job-match-demo.streamlit.app](https://ramil-job-match-demo.streamlit.app/).
The public app always includes a validated, pre-generated OpenAI report using
fictional inputs. Its optional live analyzer is protected by Google sign-in,
persistent usage limits, input constraints, and server-side secrets.

The live public feature is disabled by default in the repository and fails
closed if authentication, quota storage, or any required secret is unavailable.
The original OpenAI Streamlit deployment remains private and unchanged.

## Features

The OpenAI agent:

1. Identifies required and preferred job qualifications.
2. Matches each requirement with evidence from the resume.
3. Clearly identifies missing or weak qualifications.
4. Suggests truthful resume improvements.
5. Generates five likely interview questions.
6. Validates the report before displaying or downloading it.
7. Provides PDF and Markdown downloads.
8. Screens public submissions before running the paid analysis.
9. Applies persistent per-account, daily, and overall public usage limits.

## OpenAI Analysis Workflow

`portfolio_app.py` always provides a public view of a saved fictional OpenAI
report. When its server-side feature flag is enabled, it also provides live
analysis to verified users. Before a paid generation can begin, the app must
successfully reserve one attempt in the persistent quota database.

`web_app.py` provides the separate private OpenAI-powered Streamlit experience.
`app.py` provides the command-line version. Both remain available for owner use.

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
- Keep API, authentication, database, and hashing secrets outside Git
- Require verified sign-in before public live analysis
- Store only a pseudonymous user identifier in the quota database
- Enforce per-account, shared daily, and overall limits atomically
- Stop safely without calling OpenAI if the quota service is unavailable
- Constrain public input length, output tokens, and model turns
- Disable sensitive agent tracing for public submissions
- Send a pseudonymous safety identifier with each public generation

## Project Structure

- `portfolio_app.py` - provides the public saved example and gated live interface.
- `public_analysis.py` - validates settings, pseudonymizes users, and enforces quotas.
- `public_openai.py` - screens and runs one constrained public OpenAI analysis.
- `web_app.py` - provides the private live OpenAI Streamlit app.
- `app.py` - runs the OpenAI-powered command-line application.
- `agent_core.py` - contains the shared OpenAI agent configuration.
- `agent_tools.py` - saves command-line reports.
- `quality_benchmark.py` - evaluates the saved OpenAI example against human labels.
- `BENCHMARK.md` - documents the evaluation method, results, and limitations.
- `PUBLIC_DEPLOYMENT.md` - documents the fail-closed public rollout sequence.
- `file_utils.py` - reads and writes project files.
- `pdf_utils.py` - converts reports into formatted PDF data.
- `report_validation.py` - validates report structure and completeness.
- `quality_check.py` - checks the command-line report.
- `database/quota_schema.sql` - creates atomic persistent quota functions.
- `tests/` - contains automated benchmark, validator, and PDF tests.
- `examples/` - contains fictional, public-safe sample inputs and output.
- `data/` - contains private local inputs and is excluded from Git.
- `outputs/` - contains generated command-line reports and is excluded from Git.
- `.streamlit/secrets.example.toml` - shows safe cloud configuration placeholders.
- `.env.example` - shows safe local configuration placeholders.
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

Start the public app:

```bash
python -m streamlit run portfolio_app.py
```

Open the local address shown in the terminal, normally:

```text
http://localhost:8501
```

With the live feature disabled, the portfolio app contains three sections:

- **View OpenAI Example** - inspect the fictional resume, job description, and
  saved OpenAI report.
- **Quality Evaluation** - compare the report's eight qualification assessments
  with human-labeled expected results.
- **How It Works** - review the architecture, safeguards, and limitations.

Opening or downloading content from this app makes no API call.

## Configure Limited Public OpenAI Analysis

The public live feature requires two external protections in addition to the
OpenAI API key:

1. **Google OpenID Connect** identifies each user through Streamlit's native
   `st.login()` flow.
2. **A dedicated Supabase quota database** stores only pseudonymous counters and
   reserves attempts atomically.

Run [`database/quota_schema.sql`](database/quota_schema.sql) once in the
dedicated Supabase project's SQL editor. Then copy the safe structure in
[`secrets.example.toml`](.streamlit/secrets.example.toml) into the local ignored
`.streamlit/secrets.toml` file or the public app's Community Cloud secrets.

The default limits are:

- 3 attempts for each verified account
- 10 attempts shared across all users per UTC day
- 100 attempts across the lifetime of the public demonstration
- 8,000 characters for each submitted document
- 3,000 maximum output tokens and one agent turn per analysis

The counters represent reserved API attempts. An attempt is counted before the
OpenAI request starts and remains counted if the provider or report validation
later fails. This conservative behavior prevents repeated failures from bypassing
the cost limits.

Keep this setting at `false` during setup and testing:

```text
ENABLE_PUBLIC_OPENAI_ANALYSIS=false
```

Change it to `true` only after Google sign-in, the quota database, the public-app
secrets, and an OpenAI spending limit have all been verified. The existing API
key value does not need to be placed in the repository or changed in the private
app.

Follow the complete fail-closed rollout sequence in
[`PUBLIC_DEPLOYMENT.md`](PUBLIC_DEPLOYMENT.md).

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
- Public live analysis is disabled by default
- Missing authentication or quota configuration fails closed
- User identifiers are pseudonymized before storage or API use
- Quota-service errors prevent OpenAI requests
- Public inputs, output size, and agent turns are constrained
- Safety screening stops flagged text before paid generation
- Database functions use row locks for atomic limits

## Privacy and Cost

The saved-example sections read only the fictional files committed in the
`examples/` directory and make no API call.

The optional public live section requires sign-in and asks users to submit only
fictional or redacted text. The app does not persist submitted resume text, job
descriptions, or generated reports. The quota database stores a salted,
pseudonymous account key and counters, not the user's email or documents.

Each accepted public submission reserves one quota attempt, runs OpenAI safety
screening, and can make at most one paid report-generation request. API and
authentication credentials stay in Streamlit secrets and never enter the
browser or repository.

The private web app and command-line application send resume and job-description
text to the OpenAI API. The command-line version saves its completed report in
`outputs/`. The private web app creates downloads in the active session.

The `.env`, `.streamlit/secrets.toml`, `data/`, and `outputs/` paths are excluded
from Git.

## Current Limitations

- Public usage limits reduce financial risk but cannot prove that one person has
  only one identity-provider account.
- The public feature depends on Google OpenID Connect, Supabase, Streamlit
  Community Cloud, and OpenAI availability.
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
