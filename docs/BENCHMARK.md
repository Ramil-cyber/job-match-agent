# OpenAI Quality Benchmark

## Purpose

This benchmark evaluates a previously generated OpenAI job-match report against
human-labeled expected assessments.

Running the benchmark makes no OpenAI API call. It uses the fictional,
public-safe example in the `examples/` directory.

## Method

The sample job description contains eight required or preferred qualifications.
Each qualification was labeled as `Meets`, `Partial`, or `Missing` based only
on the fictional resume. The benchmark normalizes the saved OpenAI report to
those three classes and compares its assessments with the expected labels.

It also counts:

- False-positive qualification claims, where a missing qualification is
  presented as demonstrated
- Missed demonstrated matches, where a demonstrated qualification is presented
  as missing

## Results

| Requirement | Expected | Saved OpenAI |
|---|---|---|
| Quantitative bachelor's degree | Meets | Meets |
| Two years of analytics experience | Meets | Meets |
| Python and SQL | Meets | Meets |
| Forecasting or machine learning | Meets | Meets |
| AWS | Missing | Missing |
| Written and verbal communication | Partial | Partial |
| Natural language processing | Missing | Missing |
| Executive dashboards | Partial | Partial |

| Metric | Saved OpenAI |
|---|---:|
| Requirement classifications matching expected labels | 8/8 |
| False-positive qualification claims | 0 |
| Missed demonstrated matches | 0 |

## Interpretation

The saved OpenAI report matched all eight expected qualification labels in this
one fictional scenario and made no false-positive qualification claims.

This is a reproducible smoke test, not evidence of general 100% accuracy. A
broader evaluation would require more labeled resumes and job descriptions
covering strong, moderate, weak, ambiguous, and adversarial cases.

## Reproduce the Benchmark

Install the project dependencies, then run:

```bash
python -m job_match_agent.quality_benchmark
```

The script validates the saved OpenAI report, extracts its requirement
assessments, and prints the evaluation metrics. It does not make an API call.
