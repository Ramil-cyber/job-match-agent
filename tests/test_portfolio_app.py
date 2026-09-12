import os
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_APP_PATH = PROJECT_ROOT / "portfolio_app.py"


class PortfolioAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous_setting = os.environ.get("ENABLE_PUBLIC_OPENAI_ANALYSIS")
        os.environ["ENABLE_PUBLIC_OPENAI_ANALYSIS"] = "false"

        try:
            cls.app = AppTest.from_file(PORTFOLIO_APP_PATH).run(timeout=30)
        finally:
            if previous_setting is None:
                os.environ.pop("ENABLE_PUBLIC_OPENAI_ANALYSIS", None)
            else:
                os.environ["ENABLE_PUBLIC_OPENAI_ANALYSIS"] = previous_setting

    def test_public_portfolio_renders_without_exceptions(self):
        self.assertEqual(len(self.app.exception), 0)

    def test_public_portfolio_has_openai_only_tabs(self):
        self.assertEqual(
            [tab.label for tab in self.app.tabs],
            [
                "View OpenAI Example",
                "Quality Evaluation",
                "How It Works",
            ],
        )

    def test_disabled_public_analysis_has_no_input_fields(self):
        self.assertEqual(len(self.app.text_area), 0)

    def test_enabled_feature_without_auth_fails_closed(self):
        settings = {
            "ENABLE_PUBLIC_OPENAI_ANALYSIS": "true",
            "OPENAI_API_KEY": "test-key",
            "SUPABASE_URL": "https://project.supabase.co",
            "SUPABASE_SECRET_KEY": "test-secret-key",
            "USER_HASH_SALT": "test-hash-salt-with-at-least-32-characters",
        }

        with patch.dict(os.environ, settings, clear=False):
            app = AppTest.from_file(PORTFOLIO_APP_PATH).run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.text_area), 0)
        self.assertEqual(
            [tab.label for tab in app.tabs],
            [
                "Live OpenAI Analysis",
                "View OpenAI Example",
                "Quality Evaluation",
                "How It Works",
            ],
        )
        self.assertTrue(any("safely disabled" in error.value for error in app.error))


if __name__ == "__main__":
    unittest.main()
