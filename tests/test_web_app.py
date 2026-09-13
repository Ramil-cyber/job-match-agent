import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_APP_PATH = PROJECT_ROOT / "web_app.py"


class PrivateWebAppTests(unittest.TestCase):
    def build_app(self):
        """Run a fresh private interface without submitting an OpenAI call."""

        return AppTest.from_file(WEB_APP_PATH).run(timeout=30)

    def test_paste_controls_render_without_exceptions(self):
        app = self.build_app()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(
            [radio.label for radio in app.radio],
            ["Resume input method", "Job Description input method"],
        )
        self.assertTrue(
            all(radio.options == ["Paste text", "Upload file"] for radio in app.radio)
        )
        self.assertEqual(
            [text_area.label for text_area in app.text_area],
            ["Resume", "Job Description"],
        )
        self.assertTrue(all(field.max_chars == 10_000 for field in app.text_area))

    def test_upload_choice_displays_file_uploader(self):
        app = self.build_app()

        app.radio[0].set_value("Upload file").run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.get("file_uploader")), 1)
        self.assertEqual(
            [text_area.label for text_area in app.text_area],
            ["Job Description"],
        )

    def test_empty_submission_is_rejected_before_openai(self):
        app = self.build_app()

        app.button[0].click().run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("provide both" in error.value for error in app.error))
        self.assertIsNone(app.session_state["job_match_report"])


if __name__ == "__main__":
    unittest.main()
