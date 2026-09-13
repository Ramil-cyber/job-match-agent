import unittest
from pathlib import Path

import tomllib

from job_match_agent.streamlit_ui import (
    APP_STYLES,
    build_feature_grid_html,
    build_hero_html,
    build_section_header_html,
    build_workflow_html,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STREAMLIT_CONFIG_PATH = PROJECT_ROOT / ".streamlit" / "config.toml"


class StreamlitUiTests(unittest.TestCase):
    def test_hero_contains_product_message_and_badges(self):
        markup = build_hero_html(
            eyebrow="Career intelligence",
            title="Match your experience.",
            highlighted_title="Plan your next move.",
            description="Evidence-led guidance.",
            badges=("Private", "PDF · DOCX · TXT"),
        )

        self.assertIn("jma-hero", markup)
        self.assertIn("Plan your next move.", markup)
        self.assertEqual(markup.count('class="jma-chip"'), 2)

    def test_hero_escapes_dynamic_text(self):
        markup = build_hero_html(
            eyebrow="<script>",
            title="A & B",
            highlighted_title='"Safe"',
            description="<strong>description</strong>",
            badges=("<badge>",),
        )

        self.assertNotIn("<script>", markup)
        self.assertNotIn("<strong>description</strong>", markup)
        self.assertIn("&lt;script&gt;", markup)
        self.assertIn("A &amp; B", markup)
        self.assertIn("&lt;badge&gt;", markup)

    def test_section_header_escapes_text(self):
        markup = build_section_header_html(
            eyebrow="One < two",
            title="Safe & clear",
            description="Use > with care",
        )

        self.assertIn("One &lt; two", markup)
        self.assertIn("Safe &amp; clear", markup)
        self.assertIn("Use &gt; with care", markup)

    def test_workflow_numbers_steps_and_escapes_text(self):
        markup = build_workflow_html(
            (("Resume", "Add <text>"), ("Role", "Add requirements"))
        )

        self.assertIn(">01<", markup)
        self.assertIn(">02<", markup)
        self.assertIn("Add &lt;text&gt;", markup)
        self.assertEqual(markup.count('class="jma-step"'), 2)

    def test_feature_grid_escapes_card_content(self):
        markup = build_feature_grid_html(
            (("01", "Protected <agent>", "Sign-in & quota"),)
        )

        self.assertIn("Protected &lt;agent&gt;", markup)
        self.assertIn("Sign-in &amp; quota", markup)
        self.assertEqual(markup.count('class="jma-feature-card"'), 1)

    def test_theme_and_accessibility_rules_are_configured(self):
        with STREAMLIT_CONFIG_PATH.open("rb") as config_file:
            config = tomllib.load(config_file)

        self.assertEqual(config["theme"]["base"], "dark")
        self.assertEqual(config["theme"]["primaryColor"], "#2DD4BF")
        self.assertIn(":focus-visible", APP_STYLES)
        self.assertIn("prefers-reduced-motion", APP_STYLES)


if __name__ == "__main__":
    unittest.main()
