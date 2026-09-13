"""Shared presentation components for the Streamlit applications."""

from __future__ import annotations

from collections.abc import Sequence
from html import escape

import streamlit as st

APP_STYLES = """
<style>
:root {
  --jma-ink: #f4f7fb;
  --jma-muted: #a8b7ca;
  --jma-teal: #2dd4bf;
  --jma-cyan: #67e8f9;
  --jma-blue: #60a5fa;
  --jma-panel: rgba(16, 28, 47, 0.82);
  --jma-border: rgba(148, 163, 184, 0.20);
}

[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 12% 0%, rgba(45, 212, 191, 0.10), transparent 28rem),
    radial-gradient(circle at 92% 12%, rgba(96, 165, 250, 0.10), transparent 30rem),
    #07111f;
}

[data-testid="stHeader"] {
  background: rgba(7, 17, 31, 0.70);
  backdrop-filter: blur(14px);
}

.block-container {
  max-width: 74rem;
  padding-top: 2.25rem;
  padding-bottom: 4.5rem;
}

.jma-hero {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  margin: 0 0 1.5rem;
  padding: clamp(1.6rem, 4vw, 3.2rem);
  border: 1px solid rgba(103, 232, 249, 0.18);
  border-radius: 1.5rem;
  background:
    linear-gradient(128deg, rgba(15, 39, 62, 0.98), rgba(11, 25, 43, 0.96) 55%, rgba(13, 49, 54, 0.92));
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.24);
}

.jma-hero::before {
  content: "";
  position: absolute;
  z-index: -1;
  width: 22rem;
  height: 22rem;
  top: -12rem;
  right: -5rem;
  border-radius: 999px;
  background: rgba(45, 212, 191, 0.17);
  filter: blur(4px);
}

.jma-eyebrow {
  margin: 0 0 0.85rem;
  color: var(--jma-cyan);
  font-size: 0.76rem;
  font-weight: 750;
  letter-spacing: 0.13em;
  text-transform: uppercase;
}

.jma-hero h1 {
  max-width: 54rem;
  margin: 0;
  color: var(--jma-ink);
  font-size: clamp(2.3rem, 6vw, 4.6rem);
  line-height: 0.99;
  letter-spacing: -0.052em;
}

.jma-hero h1 span {
  color: var(--jma-teal);
}

.jma-hero-copy {
  max-width: 46rem;
  margin: 1.25rem 0 0;
  color: #c5d2e2;
  font-size: clamp(1rem, 2vw, 1.14rem);
  line-height: 1.65;
}

.jma-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 1.45rem;
}

.jma-chip {
  display: inline-flex;
  align-items: center;
  min-height: 2rem;
  padding: 0.35rem 0.7rem;
  border: 1px solid rgba(103, 232, 249, 0.20);
  border-radius: 999px;
  background: rgba(7, 17, 31, 0.45);
  color: #d7e4f2;
  font-size: 0.78rem;
  font-weight: 650;
}

.jma-section-heading {
  margin: 1.65rem 0 1rem;
}

.jma-section-heading h2 {
  margin: 0;
  color: var(--jma-ink);
  font-size: clamp(1.65rem, 4vw, 2.35rem);
  line-height: 1.12;
  letter-spacing: -0.035em;
}

.jma-section-heading p:last-child {
  max-width: 48rem;
  margin: 0.65rem 0 0;
  color: var(--jma-muted);
  line-height: 1.6;
}

.jma-steps,
.jma-feature-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.8rem;
  margin: 1rem 0 1.35rem;
}

.jma-step,
.jma-feature-card {
  min-height: 7.25rem;
  padding: 1rem 1.05rem;
  border: 1px solid var(--jma-border);
  border-radius: 1rem;
  background: linear-gradient(145deg, rgba(16, 28, 47, 0.90), rgba(11, 24, 40, 0.82));
}

.jma-step-number {
  display: inline-grid;
  place-items: center;
  width: 1.8rem;
  height: 1.8rem;
  margin-bottom: 0.7rem;
  border-radius: 0.55rem;
  background: rgba(45, 212, 191, 0.13);
  color: var(--jma-teal);
  font-size: 0.75rem;
  font-weight: 800;
}

.jma-step strong,
.jma-feature-card strong {
  display: block;
  margin-bottom: 0.3rem;
  color: var(--jma-ink);
  font-size: 0.95rem;
}

.jma-step p,
.jma-feature-card p {
  margin: 0;
  color: var(--jma-muted);
  font-size: 0.84rem;
  line-height: 1.48;
}

.jma-feature-icon {
  display: inline-block;
  margin-bottom: 0.75rem;
  color: var(--jma-cyan);
  font-size: 1.15rem;
  font-weight: 800;
}

.jma-footer {
  margin-top: 2.7rem;
  padding-top: 1.1rem;
  border-top: 1px solid var(--jma-border);
  color: #7f91a8;
  font-size: 0.78rem;
  text-align: center;
}

/* Native Streamlit components */
.stTabs [data-baseweb="tab-list"] {
  gap: 0.35rem;
  padding: 0.35rem;
  border: 1px solid var(--jma-border);
  border-radius: 0.95rem;
  background: rgba(9, 21, 37, 0.72);
}

.stTabs [data-baseweb="tab"] {
  min-height: 2.75rem;
  padding: 0.55rem 0.85rem;
  border-radius: 0.7rem;
  color: #aebdd0;
  font-weight: 650;
}

.stTabs [aria-selected="true"] {
  background: rgba(45, 212, 191, 0.12);
  color: #ecfeff;
}

.stTabs [data-baseweb="tab-highlight"] {
  background-color: var(--jma-teal);
}

[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--jma-border);
  border-radius: 1rem;
  background: rgba(11, 23, 39, 0.52);
}

[data-testid="stMetric"] {
  min-height: 7rem;
  padding: 1rem 1.05rem;
  border: 1px solid var(--jma-border);
  border-radius: 1rem;
  background: var(--jma-panel);
}

[data-testid="stMetricLabel"] {
  color: var(--jma-muted);
}

[data-testid="stMetricValue"] {
  color: var(--jma-ink);
  letter-spacing: -0.04em;
}

[data-testid="stAlert"] {
  border-radius: 0.9rem;
}

[data-testid="stFileUploaderDropzone"] {
  min-height: 8.5rem;
  border-color: rgba(103, 232, 249, 0.24);
  border-radius: 0.85rem;
  background: rgba(9, 22, 38, 0.70);
}

[data-baseweb="textarea"] textarea {
  line-height: 1.55;
}

[data-baseweb="textarea"],
[data-baseweb="input"] {
  border-radius: 0.8rem;
}

.stButton > button,
.stDownloadButton > button,
.stLinkButton > a {
  min-height: 2.9rem;
  border-radius: 0.78rem;
  font-weight: 700;
  transition: transform 150ms ease, border-color 150ms ease, box-shadow 150ms ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
.stLinkButton > a:hover {
  transform: translateY(-1px);
  border-color: rgba(103, 232, 249, 0.52);
}

.stButton > button[kind="primary"] {
  color: #04201d;
  box-shadow: 0 10px 28px rgba(45, 212, 191, 0.16);
}

[data-testid="stExpander"] {
  overflow: hidden;
  border-color: var(--jma-border);
  border-radius: 0.9rem;
  background: rgba(11, 23, 39, 0.42);
}

[data-testid="stTable"] {
  overflow-x: auto;
  border: 1px solid var(--jma-border);
  border-radius: 0.9rem;
}

[data-testid="stMarkdownContainer"] table {
  display: block;
  overflow-x: auto;
  width: 100%;
}

[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {
  letter-spacing: -0.025em;
}

*:focus-visible {
  outline: 3px solid rgba(103, 232, 249, 0.72) !important;
  outline-offset: 2px !important;
}

@media (max-width: 760px) {
  .block-container {
    padding-top: 1.15rem;
    padding-left: 1rem;
    padding-right: 1rem;
  }

  .jma-hero {
    border-radius: 1.1rem;
  }

  .jma-steps,
  .jma-feature-grid {
    grid-template-columns: 1fr;
  }

  .jma-step,
  .jma-feature-card {
    min-height: auto;
  }

  .stTabs [data-baseweb="tab-list"] {
    overflow-x: auto;
    justify-content: flex-start;
  }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    transition: none !important;
  }
}
</style>
"""


def apply_shared_styles() -> None:
    """Apply the shared, responsive visual system."""

    st.markdown(APP_STYLES, unsafe_allow_html=True)


def build_hero_html(
    *,
    eyebrow: str,
    title: str,
    highlighted_title: str,
    description: str,
    badges: Sequence[str],
) -> str:
    """Return safe static markup for the application hero."""

    badge_html = "".join(
        f'<span class="jma-chip">{escape(badge)}</span>' for badge in badges
    )
    return (
        '<section class="jma-hero">'
        f'<p class="jma-eyebrow">{escape(eyebrow)}</p>'
        f"<h1>{escape(title)} <span>{escape(highlighted_title)}</span></h1>"
        f'<p class="jma-hero-copy">{escape(description)}</p>'
        f'<div class="jma-chip-row">{badge_html}</div>'
        "</section>"
    )


def render_hero(
    *,
    eyebrow: str,
    title: str,
    highlighted_title: str,
    description: str,
    badges: Sequence[str],
) -> None:
    """Render the application hero."""

    st.markdown(
        build_hero_html(
            eyebrow=eyebrow,
            title=title,
            highlighted_title=highlighted_title,
            description=description,
            badges=badges,
        ),
        unsafe_allow_html=True,
    )


def build_section_header_html(*, eyebrow: str, title: str, description: str) -> str:
    """Return safe markup for a section heading."""

    return (
        '<header class="jma-section-heading">'
        f'<p class="jma-eyebrow">{escape(eyebrow)}</p>'
        f"<h2>{escape(title)}</h2>"
        f"<p>{escape(description)}</p>"
        "</header>"
    )


def render_section_header(*, eyebrow: str, title: str, description: str) -> None:
    """Render one consistently styled section heading."""

    st.markdown(
        build_section_header_html(
            eyebrow=eyebrow,
            title=title,
            description=description,
        ),
        unsafe_allow_html=True,
    )


def build_workflow_html(steps: Sequence[tuple[str, str]]) -> str:
    """Return safe markup for a compact numbered workflow."""

    cards = "".join(
        (
            '<div class="jma-step">'
            f'<span class="jma-step-number">{index:02d}</span>'
            f"<strong>{escape(title)}</strong>"
            f"<p>{escape(description)}</p>"
            "</div>"
        )
        for index, (title, description) in enumerate(steps, start=1)
    )
    return f'<div class="jma-steps">{cards}</div>'


def render_workflow_steps(steps: Sequence[tuple[str, str]]) -> None:
    """Render a numbered workflow."""

    st.markdown(build_workflow_html(steps), unsafe_allow_html=True)


def build_feature_grid_html(cards: Sequence[tuple[str, str, str]]) -> str:
    """Return safe markup for explanatory feature cards."""

    card_html = "".join(
        (
            '<article class="jma-feature-card">'
            f'<span class="jma-feature-icon">{escape(icon)}</span>'
            f"<strong>{escape(title)}</strong>"
            f"<p>{escape(description)}</p>"
            "</article>"
        )
        for icon, title, description in cards
    )
    return f'<div class="jma-feature-grid">{card_html}</div>'


def render_feature_grid(cards: Sequence[tuple[str, str, str]]) -> None:
    """Render explanatory feature cards."""

    st.markdown(build_feature_grid_html(cards), unsafe_allow_html=True)


def render_footer() -> None:
    """Render a restrained product footer."""

    st.markdown(
        '<footer class="jma-footer">Job Match Agent · Evidence-led guidance · '
        "Human review required</footer>",
        unsafe_allow_html=True,
    )
