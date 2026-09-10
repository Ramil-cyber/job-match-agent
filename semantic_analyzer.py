import re
from dataclasses import dataclass
from typing import Protocol

import numpy as np

MAX_REQUIREMENTS = 12
MAX_EVIDENCE_ITEMS = 60


class EmbeddingModel(Protocol):
    """Interface implemented by FastEmbed and the test double."""

    def query_embed(self, query): ...

    def passage_embed(self, texts): ...


@dataclass(frozen=True)
class Requirement:
    category: str
    text: str


@dataclass(frozen=True)
class RequirementMatch:
    requirement: Requirement
    evidence: str
    assessment: str
    similarity: float


CATEGORY_HEADINGS = {
    "Preferred": ("preferred", "desired", "nice to have", "bonus"),
    "Required": (
        "required",
        "requirements",
        "minimum qualification",
        "basic qualification",
        "must have",
        "what you need",
        "what you'll need",
    ),
}

REQUIREMENT_CUES = (
    "ability",
    "degree",
    "experience",
    "familiarity",
    "knowledge",
    "must",
    "preferred",
    "proficiency",
    "required",
    "skill",
    "years",
)

INJECTION_PHRASES = (
    "api key",
    "disregard the",
    "ignore all",
    "ignore previous",
    "reveal the prompt",
    "system message",
    "system prompt",
)

GENERIC_HEADINGS = {
    "education",
    "experience",
    "professional experience",
    "professional summary",
    "qualifications",
    "skills",
    "summary",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "using",
    "with",
}

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

# Explicit checks prevent semantic similarity from claiming that a named skill
# exists when the resume does not actually contain it.
CONCEPT_ALIASES = {
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure", "microsoft azure"),
    "bachelor's degree": (
        "bachelor's degree",
        "bachelors degree",
        "bachelor of arts",
        "bachelor of science",
        "b.a.",
        "b.s.",
    ),
    "communication": (
        "communication",
        "communicated",
        "presented",
        "presentation",
        "stakeholder",
    ),
    "data analytics": ("data analytics", "analytics", "data analysis", "analyst"),
    "data science": ("data science", "data scientist"),
    "data visualization": ("data visualization", "visualization", "visualisation"),
    "Databricks": ("databricks",),
    "dashboard": ("dashboard", "dashboards", "business intelligence"),
    "Docker": ("docker", "containerization", "containerisation"),
    "Excel": ("excel", "microsoft excel"),
    "executive audience": (
        "executive",
        "c-suite",
        "senior leadership",
        "leadership team",
    ),
    "forecasting": ("forecasting", "forecast", "time series", "time-series"),
    "GCP": ("gcp", "google cloud", "google cloud platform"),
    "Git": ("git", "github", "gitlab"),
    "Java": ("java",),
    "JavaScript": ("javascript",),
    "Kubernetes": ("kubernetes", "k8s"),
    "LLMs": ("large language model", "large language models", "llm", "llms"),
    "machine learning": (
        "machine learning",
        "ml",
        "predictive model",
        "predictive modeling",
        "predictive modelling",
    ),
    "master's degree": (
        "master's degree",
        "masters degree",
        "master of arts",
        "master of science",
        "m.a.",
        "m.s.",
    ),
    "NLP": (
        "natural language processing",
        "nlp",
        "text analytics",
        "text classification",
    ),
    "PhD": ("phd", "ph.d.", "doctorate", "doctoral degree"),
    "Power BI": ("power bi", "powerbi"),
    "Python": ("python",),
    "R": ("r", "r programming"),
    "Salesforce": ("salesforce",),
    "scikit-learn": ("scikit-learn", "sklearn"),
    "Snowflake": ("snowflake",),
    "Spark": ("spark", "apache spark", "pyspark"),
    "SQL": ("sql", "structured query language"),
    "statistics": ("statistics", "statistical", "statistician"),
    "Tableau": ("tableau",),
    "TensorFlow": ("tensorflow",),
    "verbal communication": (
        "verbal",
        "oral communication",
        "public speaking",
        "presented",
        "presentation",
    ),
    "written communication": (
        "written",
        "technical writing",
        "written report",
        "written reports",
        "documentation",
    ),
    "XGBoost": ("xgboost",),
}


def _normalize(text: str) -> str:
    return (
        text.casefold()
        .replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )


def _contains_phrase(text: str, phrase: str) -> bool:
    phrase_pattern = re.escape(_normalize(phrase)).replace(r"\ ", r"[-\s]+")
    return bool(re.search(rf"(?<!\w){phrase_pattern}(?!\w)", _normalize(text)))


def _clean_item(line: str) -> str:
    return re.sub(r"^\s*(?:[-*\u2022]|\d+[.)])\s+", "", line).strip()


def _heading_category(line: str) -> str | None:
    heading = re.sub(r"^[#*\s]+|[:*\s]+$", "", line).casefold()
    if not heading or len(heading) > 80:
        return None
    for category, markers in CATEGORY_HEADINGS.items():
        if any(marker in heading for marker in markers):
            return category
    return None


def _is_injected_instruction(text: str) -> bool:
    lowered = _normalize(text)
    return any(phrase in lowered for phrase in INJECTION_PHRASES)


def extract_requirements(job_description: str) -> list[Requirement]:
    """Extract required and preferred qualification bullets."""

    if not isinstance(job_description, str) or not job_description.strip():
        raise ValueError("The job description cannot be empty.")

    requirements = []
    category = "Required"

    for raw_line in job_description.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if heading_category := _heading_category(line):
            category = heading_category
            continue

        is_bullet = bool(re.match(r"^\s*(?:[-*\u2022]|\d+[.)])\s+", raw_line))
        candidate = _clean_item(line)
        if (
            is_bullet
            and len(candidate) >= 8
            and not _is_injected_instruction(candidate)
        ):
            requirements.append(Requirement(category, candidate))

    if not requirements:
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", job_description):
            candidate = _clean_item(sentence)
            lowered = _normalize(candidate)
            if (
                len(candidate) >= 12
                and any(cue in lowered for cue in REQUIREMENT_CUES)
                and not _is_injected_instruction(candidate)
            ):
                sentence_category = (
                    "Preferred" if "preferred" in lowered else "Required"
                )
                requirements.append(Requirement(sentence_category, candidate))

    unique_requirements = []
    seen = set()
    for requirement in requirements:
        key = re.sub(r"\W+", " ", requirement.text.casefold()).strip()
        if key not in seen:
            seen.add(key)
            unique_requirements.append(requirement)

    if not unique_requirements:
        raise ValueError(
            "No clear requirements were found. Use a job description with "
            "qualification bullets or requirement sentences."
        )
    return unique_requirements[:MAX_REQUIREMENTS]


def extract_resume_evidence(resume: str) -> list[str]:
    """Split a resume into short, distinct pieces of evidence."""

    if not isinstance(resume, str) or not resume.strip():
        raise ValueError("The resume cannot be empty.")

    evidence = []
    seen = set()
    for piece in re.split(r"(?<=[.!?])\s+|\n+", resume):
        candidate = _clean_item(piece)
        key = re.sub(r"\W+", " ", candidate.casefold()).strip()
        if (
            3 <= len(candidate) <= 400
            and key not in GENERIC_HEADINGS
            and key not in seen
        ):
            seen.add(key)
            evidence.append(candidate)
    return evidence[:MAX_EVIDENCE_ITEMS] or [resume.strip()[:1000]]


def _normalize_vectors(vectors) -> np.ndarray:
    matrix = np.asarray(list(vectors), dtype=float)
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _similarity_scores(model, requirements, evidence) -> tuple[np.ndarray, str]:
    if model is not None:
        queries = _normalize_vectors(
            model.query_embed([item.text for item in requirements])
        )
        passages = _normalize_vectors(model.passage_embed(evidence))
        return queries @ passages.T, "local semantic embeddings"

    # Deterministic fallback keeps the public demo available if model loading fails.
    rows = []
    for requirement in requirements:
        requirement_tokens = {
            token
            for token in re.findall(r"[a-z0-9+#.]+", _normalize(requirement.text))
            if token not in STOPWORDS and len(token) > 1
        }
        row = []
        for evidence_item in evidence:
            evidence_tokens = {
                token
                for token in re.findall(r"[a-z0-9+#.]+", _normalize(evidence_item))
                if token not in STOPWORDS and len(token) > 1
            }
            shared = requirement_tokens & evidence_tokens
            denominator = max(1, min(len(requirement_tokens), len(evidence_tokens)))
            overlap = len(shared) / denominator
            row.append(0.42 + (0.45 * overlap) if shared else 0.0)
        rows.append(row)
    return np.asarray(rows, dtype=float), "lexical fallback"


def _concepts_in(text: str) -> list[str]:
    return [
        name
        for name, aliases in CONCEPT_ALIASES.items()
        if any(_contains_phrase(text, alias) for alias in aliases)
    ]


def _evidence_for_concept(concept: str, evidence: list[str]) -> list[int]:
    aliases = CONCEPT_ALIASES[concept]
    return [
        index
        for index, item in enumerate(evidence)
        if any(_contains_phrase(item, alias) for alias in aliases)
    ]


def _stated_years(text: str) -> list[int]:
    number_pattern = "|".join([r"\d+", *NUMBER_WORDS])
    values = re.findall(
        rf"\b({number_pattern})\+?\s+(?:years?|yrs?)\b",
        _normalize(text),
    )
    return [int(value) if value.isdigit() else NUMBER_WORDS[value] for value in values]


def match_requirements(resume, job_description, embedding_model=None):
    """Match requirements to resume evidence without using a paid API."""

    requirements = extract_requirements(job_description)
    evidence = extract_resume_evidence(resume)
    scores, engine_name = _similarity_scores(embedding_model, requirements, evidence)
    resume_years = max(_stated_years(resume), default=None)
    matches = []

    for index, requirement in enumerate(requirements):
        score_row = scores[index]
        similarity = float(np.max(score_row))
        concepts = _concepts_in(requirement.text)
        concept_indexes = {
            concept: _evidence_for_concept(concept, evidence) for concept in concepts
        }
        matched_concepts = [
            concept for concept, indexes in concept_indexes.items() if indexes
        ]
        required_years = max(_stated_years(requirement.text), default=None)

        if (
            required_years is not None
            and resume_years is not None
            and resume_years < required_years
        ):
            assessment = "Not demonstrated"
        elif concepts:
            coverage = len(matched_concepts) / len(concepts)
            if coverage == 1:
                assessment = "Meets" if similarity >= 0.45 else "Partially demonstrated"
            elif coverage == 0:
                assessment = "Not demonstrated"
            elif " or " in _normalize(requirement.text) and similarity >= 0.68:
                assessment = "Meets"
            else:
                assessment = "Partially demonstrated"
        elif required_years is not None and resume_years is not None:
            assessment = "Meets"
        elif similarity >= 0.70:
            assessment = "Meets"
        elif similarity >= 0.52:
            assessment = "Partially demonstrated"
        else:
            assessment = "Not demonstrated"

        if assessment == "Not demonstrated":
            selected_evidence = "Not found in the resume"
        else:
            selected_indexes = []
            for concept in matched_concepts:
                indexes = concept_indexes[concept]
                best_index = max(indexes, key=lambda item: score_row[item])
                if best_index not in selected_indexes:
                    selected_indexes.append(best_index)
            if not selected_indexes:
                selected_indexes.append(int(np.argmax(score_row)))
            selected_evidence = "; ".join(
                evidence[item] for item in selected_indexes[:2]
            )

        matches.append(
            RequirementMatch(requirement, selected_evidence, assessment, similarity)
        )
    return matches, engine_name


def _short(text: str, limit: int = 150) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip().rstrip(".")
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rsplit(" ", 1)[0] + "..."


def _phrase(text: str, limit: int = 150) -> str:
    value = _short(text, limit)
    return value[:1].lower() + value[1:]


def _table_cell(text: str) -> str:
    return re.sub(r"\s+", " ", text).replace("|", r"\|").strip()


def _overall_fit(matches) -> str:
    required = [item for item in matches if item.requirement.category == "Required"]
    required = required or matches
    meets = sum(item.assessment == "Meets" for item in required)
    partial = sum(item.assessment == "Partially demonstrated" for item in required)
    missing = sum(item.assessment == "Not demonstrated" for item in required)
    coverage = (meets + (0.5 * partial)) / len(required)
    fit = (
        "Strong"
        if coverage >= 0.80 and missing <= 1
        else "Moderate" if coverage >= 0.45 else "Weak"
    )
    return (
        f"{fit}. The local analyzer found {meets} of {len(required)} required "
        f"qualifications demonstrated, {partial} partially demonstrated, and "
        f"{missing} not demonstrated."
    )


def _interview_questions(matches) -> list[str]:
    order = {"Not demonstrated": 0, "Partially demonstrated": 1, "Meets": 2}
    ranked = sorted(
        enumerate(matches),
        key=lambda item: (
            order[item[1].assessment],
            item[1].requirement.category != "Required",
            item[0],
        ),
    )
    questions = []
    for _, match in ranked:
        requirement = _phrase(match.requirement.text, 130)
        if match.assessment == "Not demonstrated":
            question = (
                f"The role asks for {requirement}. Do you have relevant experience "
                "that is not currently shown on your resume?"
            )
        elif match.assessment == "Partially demonstrated":
            question = (
                f"Can you explain how your experience demonstrates {requirement}?"
            )
        else:
            question = (
                f"Can you walk me through an example that demonstrates {requirement}?"
            )
        questions.append(question)
        if len(questions) == 5:
            return questions

    fallbacks = (
        "Why are you interested in this role?",
        "Which accomplishment best demonstrates your fit for this position?",
        "How do you verify the quality of your work?",
        "How do you communicate findings to nontechnical stakeholders?",
        "Which skill would you prioritize developing for this role?",
    )
    return (questions + list(fallbacks))[:5]


def create_semantic_job_match_report(resume, job_description, embedding_model=None):
    """Create a validated-report-compatible result without a paid API call."""

    if not isinstance(resume, str) or not resume.strip():
        raise ValueError("The resume cannot be empty.")
    if not isinstance(job_description, str) or not job_description.strip():
        raise ValueError("The job description cannot be empty.")

    matches, engine_name = match_requirements(resume, job_description, embedding_model)
    lines = [
        "# Job Match Report",
        "",
        "## Overall Fit",
        _overall_fit(matches),
        "",
        "## Requirement Matches",
        "",
        "| Requirement | Resume Evidence | Assessment |",
        "|---|---|---|",
    ]
    for match in matches:
        requirement = (
            f"**{match.requirement.category}:** {_table_cell(match.requirement.text)}"
        )
        lines.append(
            f"| {requirement} | {_table_cell(match.evidence)} | {match.assessment} |"
        )

    lines.extend(["", "## Missing or Weak Qualifications"])
    weak = [item for item in matches if item.assessment != "Meets"]
    if not weak:
        lines.append(
            "- No missing or weak qualifications were detected by the local analyzer. "
            "Verify nuanced requirements manually."
        )
    for match in weak:
        requirement = _short(match.requirement.text)
        if match.assessment == "Not demonstrated":
            lines.append(f"- {requirement}: Not found in the resume.")
        else:
            lines.append(
                f"- {requirement}: Only partially demonstrated by the closest "
                "resume evidence."
            )

    lines.extend(["", "## Truthful Resume Improvements"])
    suggestions = []
    for match in weak[:6]:
        requirement = _phrase(match.requirement.text, 120)
        if match.assessment == "Not demonstrated":
            suggestions.append(
                f"If you have experience related to {requirement}, add a specific "
                "example; otherwise, do not claim it."
            )
        else:
            suggestions.append(
                f"Clarify how the existing evidence relates to {requirement}, if accurate."
            )
    if not suggestions:
        suggestions = [
            "Add measurable outcomes to the strongest matched examples where accurate.",
            "Keep the most relevant demonstrated qualifications near the top of the resume.",
        ]
    lines.extend(f"- {suggestion}" for suggestion in suggestions)

    lines.extend(["", "## Likely Interview Questions"])
    lines.extend(
        f"{number}. {question}"
        for number, question in enumerate(_interview_questions(matches), start=1)
    )
    return "\n".join(lines), engine_name
