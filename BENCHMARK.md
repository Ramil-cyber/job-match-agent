# Quality Benchmark

## Purpose

This benchmark provides a transparent, reproducible comparison between:

- The free public analyzer using local semantic embeddings and explicit skill checks
- A previously generated report from the private OpenAI agent
- Human-labeled expected assessments

Running the benchmark makes no OpenAI API call. It uses fictional, public-safe
inputs from the `examples/` directory.

## Method

The sample job description contains eight required or preferred qualifications.
Each qualification was labeled as `Meets`, `Partial`, or `Missing` based only on
the fictional resume. The benchmark normalizes both reports to those three
classes and compares them with the expected labels.

It also counts false-positive qualification claims, where a report states that a
missing qualification is demonstrated.

## Results

| Requirement | Expected | Free Semantic | Saved OpenAI |
|---|---|---|---|
| Quantitative bachelor's degree | Meets | Meets | Meets |
| Two years of analytics experience | Meets | Meets | Meets |
| Python and SQL | Meets | Meets | Meets |
| Forecasting or machine learning | Meets | Meets | Meets |
| AWS | Missing | Missing | Missing |
| Written and verbal communication | Partial | Partial | Partial |
| Natural language processing | Missing | Missing | Missing |
| Executive dashboards | Partial | Partial | Partial |

| Metric | Free Semantic | Saved OpenAI |
|---|---:|---:|
| Requirement classifications matching expected labels | 8/8 | 8/8 |
| False-positive qualification claims | 0 | 0 |

## Interpretation

Both modes correctly classified all eight qualifications in this one fictional
scenario. The saved OpenAI report provides more tailored reasoning, resume
improvements, and interview questions. The free analyzer produces a more
predictable, templated report without per-analysis API charges.

This benchmark is a smoke test, not evidence of general 100% accuracy. A broader
evaluation would require more labeled resumes and job descriptions covering
strong, moderate, weak, ambiguous, and adversarial cases.

## Reproduce the Benchmark

Install the project dependencies, then run:

```bash
python quality_benchmark.py
```

The script loads the fixed open-source embedding model, generates a new free
report, reads the saved OpenAI example, and prints the comparison metrics.
