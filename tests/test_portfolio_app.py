import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_APP_PATH = PROJECT_ROOT / "portfolio_app.py"


class PortfolioAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = AppTest.from_file(PORTFOLIO_APP_PATH).run(timeout=30)

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


if __name__ == "__main__":
    unittest.main()
