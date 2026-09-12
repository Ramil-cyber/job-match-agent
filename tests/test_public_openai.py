import asyncio
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from public_analysis import load_public_analysis_config
from public_openai import PublicInputRejectedError, run_public_openai_analysis

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_REPORT = (PROJECT_ROOT / "examples" / "sample_job_match_report.md").read_text(
    encoding="utf-8"
)

VALID_SETTINGS = {
    "ENABLE_PUBLIC_OPENAI_ANALYSIS": "true",
    "OPENAI_API_KEY": "test-openai-key",
    "SUPABASE_URL": "https://project.supabase.co",
    "SUPABASE_SECRET_KEY": "test-secret-key",
    "USER_HASH_SALT": "test-user-hash-salt-with-32-characters",
}


class PublicOpenAIWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.config = load_public_analysis_config(VALID_SETTINGS)
        self.moderation_client = MagicMock()
        self.moderation_client.moderations.create = AsyncMock(
            return_value=SimpleNamespace(results=[SimpleNamespace(flagged=False)])
        )
        self.moderation_client.close = AsyncMock()

    @patch("public_openai.Runner.run", new_callable=AsyncMock)
    @patch("public_openai.AsyncOpenAI")
    def test_safe_input_runs_one_constrained_analysis(
        self,
        mocked_openai_class,
        mocked_runner,
    ):
        mocked_openai_class.return_value = self.moderation_client
        mocked_runner.return_value = SimpleNamespace(final_output=SAMPLE_REPORT)

        report = asyncio.run(
            run_public_openai_analysis(
                resume="R" * 200,
                job_description="J" * 200,
                config=self.config,
                safety_identifier="job_match_123",
            )
        )

        self.assertEqual(report, SAMPLE_REPORT.strip())
        self.moderation_client.moderations.create.assert_awaited_once()
        self.moderation_client.close.assert_awaited_once()
        mocked_runner.assert_awaited_once()
        _, analysis_request = mocked_runner.call_args.args
        self.assertIn("--- RESUME START ---", analysis_request)
        self.assertEqual(mocked_runner.call_args.kwargs["max_turns"], 1)
        run_config = mocked_runner.call_args.kwargs["run_config"]
        self.assertTrue(run_config.tracing_disabled)
        self.assertFalse(run_config.trace_include_sensitive_data)
        self.assertFalse(run_config.model_settings.store)
        self.assertEqual(
            run_config.model_settings.max_tokens,
            self.config.max_output_tokens,
        )
        self.assertEqual(
            run_config.model_settings.extra_args["safety_identifier"],
            "job_match_123",
        )

    @patch("public_openai.Runner.run", new_callable=AsyncMock)
    @patch("public_openai.AsyncOpenAI")
    def test_flagged_input_stops_before_paid_analysis(
        self,
        mocked_openai_class,
        mocked_runner,
    ):
        self.moderation_client.moderations.create.return_value = SimpleNamespace(
            results=[SimpleNamespace(flagged=True)]
        )
        mocked_openai_class.return_value = self.moderation_client

        with self.assertRaises(PublicInputRejectedError):
            asyncio.run(
                run_public_openai_analysis(
                    resume="R" * 200,
                    job_description="J" * 200,
                    config=self.config,
                    safety_identifier="job_match_123",
                )
            )

        mocked_runner.assert_not_awaited()

    @patch("public_openai.Runner.run", new_callable=AsyncMock)
    @patch("public_openai.AsyncOpenAI")
    def test_invalid_report_is_rejected(
        self,
        mocked_openai_class,
        mocked_runner,
    ):
        mocked_openai_class.return_value = self.moderation_client
        mocked_runner.return_value = SimpleNamespace(final_output="Incomplete")

        with self.assertRaisesRegex(ValueError, "Job Match Report"):
            asyncio.run(
                run_public_openai_analysis(
                    resume="R" * 200,
                    job_description="J" * 200,
                    config=self.config,
                    safety_identifier="job_match_123",
                )
            )

    @patch("public_openai.Runner.run", new_callable=AsyncMock)
    @patch("public_openai.AsyncOpenAI")
    def test_missing_moderation_result_stops_before_paid_analysis(
        self,
        mocked_openai_class,
        mocked_runner,
    ):
        self.moderation_client.moderations.create.return_value = SimpleNamespace(
            results=[]
        )
        mocked_openai_class.return_value = self.moderation_client

        with self.assertRaisesRegex(RuntimeError, "invalid result"):
            asyncio.run(
                run_public_openai_analysis(
                    resume="R" * 200,
                    job_description="J" * 200,
                    config=self.config,
                    safety_identifier="job_match_123",
                )
            )

        mocked_runner.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
