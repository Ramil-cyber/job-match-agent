import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from public_analysis import (
    PublicAnalysisConfigurationError,
    QuotaServiceError,
    SupabaseQuotaClient,
    auth_settings_are_valid,
    build_private_user_key,
    build_safety_identifier,
    load_public_analysis_config,
    validate_public_inputs,
)

VALID_SETTINGS = {
    "ENABLE_PUBLIC_OPENAI_ANALYSIS": "true",
    "OPENAI_API_KEY": "test-openai-key",
    "SUPABASE_URL": "https://project.supabase.co",
    "SUPABASE_SECRET_KEY": "test-secret-key",
    "USER_HASH_SALT": "test-user-hash-salt-with-32-characters",
}


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self, size=-1):
        return self.payload[:size] if size >= 0 else self.payload


class PublicAnalysisConfigTests(unittest.TestCase):
    def test_public_analysis_is_disabled_by_default(self):
        config = load_public_analysis_config({})

        self.assertFalse(config.enabled)
        self.assertFalse(config.is_ready)
        self.assertEqual(config.user_limit, 3)
        self.assertEqual(config.daily_limit, 10)
        self.assertEqual(config.total_limit, 100)

    def test_enabled_feature_reports_missing_secrets(self):
        config = load_public_analysis_config({"ENABLE_PUBLIC_OPENAI_ANALYSIS": "true"})

        self.assertEqual(
            config.missing_secret_names,
            (
                "OPENAI_API_KEY",
                "SUPABASE_URL",
                "SUPABASE_SECRET_KEY",
                "USER_HASH_SALT",
            ),
        )

    def test_complete_enabled_configuration_is_ready(self):
        config = load_public_analysis_config(VALID_SETTINGS)

        self.assertTrue(config.is_ready)
        self.assertEqual(config.missing_secret_names, ())

    def test_secret_values_are_hidden_from_configuration_repr(self):
        config = load_public_analysis_config(VALID_SETTINGS)
        rendered = repr(config)

        self.assertNotIn(VALID_SETTINGS["OPENAI_API_KEY"], rendered)
        self.assertNotIn(VALID_SETTINGS["SUPABASE_SECRET_KEY"], rendered)
        self.assertNotIn(VALID_SETTINGS["USER_HASH_SALT"], rendered)

    def test_invalid_boolean_fails_closed(self):
        with self.assertRaisesRegex(
            PublicAnalysisConfigurationError,
            "must be true or false",
        ):
            load_public_analysis_config({"ENABLE_PUBLIC_OPENAI_ANALYSIS": "sometimes"})

    def test_total_limit_must_cover_other_limits(self):
        settings = {
            **VALID_SETTINGS,
            "PUBLIC_ANALYSIS_DAILY_LIMIT": "10",
            "PUBLIC_ANALYSIS_TOTAL_LIMIT": "5",
        }

        with self.assertRaisesRegex(
            PublicAnalysisConfigurationError,
            "total analysis limit",
        ):
            load_public_analysis_config(settings)

    def test_enabled_feature_rejects_short_hash_salt(self):
        settings = {**VALID_SETTINGS, "USER_HASH_SALT": "too-short"}

        with self.assertRaisesRegex(
            PublicAnalysisConfigurationError,
            "at least 32 characters",
        ):
            load_public_analysis_config(settings)


class PublicAnalysisIdentityTests(unittest.TestCase):
    def test_private_user_key_is_stable_and_pseudonymous(self):
        first_key = build_private_user_key(
            issuer="https://accounts.example.com",
            subject="private-user-id",
            salt="secret-salt",
        )
        second_key = build_private_user_key(
            issuer="https://accounts.example.com",
            subject="private-user-id",
            salt="secret-salt",
        )

        self.assertEqual(first_key, second_key)
        self.assertEqual(len(first_key), 64)
        self.assertNotIn("private-user-id", first_key)

    def test_private_user_key_changes_with_identity(self):
        first_key = build_private_user_key(
            issuer="https://accounts.example.com",
            subject="user-one",
            salt="secret-salt",
        )
        second_key = build_private_user_key(
            issuer="https://accounts.example.com",
            subject="user-two",
            salt="secret-salt",
        )

        self.assertNotEqual(first_key, second_key)

    def test_safety_identifier_uses_only_pseudonymous_key(self):
        user_key = build_private_user_key(
            issuer="https://accounts.example.com",
            subject="private-user-id",
            salt="secret-salt",
        )

        safety_identifier = build_safety_identifier(user_key)

        self.assertTrue(safety_identifier.startswith("job_match_"))
        self.assertNotIn("private-user-id", safety_identifier)


class PublicAnalysisAuthTests(unittest.TestCase):
    def setUp(self):
        self.settings = {
            "redirect_uri": (
                "https://ramil-job-match-demo.streamlit.app/oauth2callback"
            ),
            "cookie_secret": "cookie-secret-with-at-least-32-characters",
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "server_metadata_url": (
                "https://accounts.google.com/.well-known/openid-configuration"
            ),
        }

    def test_complete_google_oidc_settings_are_valid(self):
        self.assertTrue(auth_settings_are_valid(self.settings))

    def test_short_cookie_secret_is_rejected(self):
        settings = {**self.settings, "cookie_secret": "short"}

        self.assertFalse(auth_settings_are_valid(settings))

    def test_non_callback_redirect_is_rejected(self):
        settings = {
            **self.settings,
            "redirect_uri": "https://example.com/not-the-callback",
        }

        self.assertFalse(auth_settings_are_valid(settings))


class PublicInputValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_public_analysis_config(VALID_SETTINGS)

    def test_complete_inputs_pass(self):
        message = validate_public_inputs(
            resume="R" * 200,
            job_description="J" * 200,
            config=self.config,
        )

        self.assertIsNone(message)

    def test_empty_input_is_rejected(self):
        message = validate_public_inputs(
            resume="",
            job_description="J" * 200,
            config=self.config,
        )

        self.assertIn("both", message)

    def test_short_input_is_rejected(self):
        message = validate_public_inputs(
            resume="short",
            job_description="J" * 200,
            config=self.config,
        )

        self.assertIn("complete resume", message)

    def test_oversized_input_is_rejected(self):
        message = validate_public_inputs(
            resume="R" * (self.config.max_resume_characters + 1),
            job_description="J" * 200,
            config=self.config,
        )

        self.assertIn("longer", message)


class SupabaseQuotaClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_public_analysis_config(VALID_SETTINGS)
        cls.user_key = build_private_user_key(
            issuer="https://accounts.example.com",
            subject="quota-user",
            salt="secret-salt",
        )

    def test_non_https_url_is_rejected(self):
        with self.assertRaisesRegex(
            PublicAnalysisConfigurationError,
            "Supabase HTTPS URL",
        ):
            SupabaseQuotaClient(
                supabase_url="http://project.supabase.co",
                secret_key="test-key",
            )

    @patch("public_analysis._HTTPS_OPENER.open")
    def test_read_quota_parses_valid_response(self, mocked_urlopen):
        mocked_urlopen.return_value = FakeResponse(
            [
                {
                    "allowed": True,
                    "user_used": 1,
                    "daily_used": 2,
                    "total_used": 8,
                    "usage_date": "2026-09-11",
                    "denial_reason": None,
                }
            ]
        )
        client = SupabaseQuotaClient(
            supabase_url=VALID_SETTINGS["SUPABASE_URL"],
            secret_key=VALID_SETTINGS["SUPABASE_SECRET_KEY"],
        )

        decision = client.read_quota(
            user_key=self.user_key,
            config=self.config,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.user_remaining, 2)
        request = mocked_urlopen.call_args.args[0]
        self.assertTrue(
            request.full_url.endswith("/rest/v1/rpc/read_public_analysis_quota")
        )
        self.assertEqual(request.method, "POST")
        self.assertEqual(
            request.get_header("Apikey"),
            VALID_SETTINGS["SUPABASE_SECRET_KEY"],
        )
        self.assertIsNone(request.get_header("Authorization"))
        self.assertNotIn(
            VALID_SETTINGS["SUPABASE_SECRET_KEY"],
            request.data.decode("utf-8"),
        )

    @patch("public_analysis._HTTPS_OPENER.open")
    def test_invalid_denial_response_fails_closed(self, mocked_urlopen):
        mocked_urlopen.return_value = FakeResponse(
            [
                {
                    "allowed": False,
                    "user_used": 1,
                    "daily_used": 2,
                    "total_used": 8,
                    "usage_date": "2026-09-11",
                    "denial_reason": "unknown",
                }
            ]
        )
        client = SupabaseQuotaClient(
            supabase_url=VALID_SETTINGS["SUPABASE_URL"],
            secret_key=VALID_SETTINGS["SUPABASE_SECRET_KEY"],
        )

        with self.assertRaises(QuotaServiceError):
            client.read_quota(user_key=self.user_key, config=self.config)

    @patch("public_analysis._HTTPS_OPENER.open")
    def test_valid_user_limit_response_is_denied(self, mocked_urlopen):
        mocked_urlopen.return_value = FakeResponse(
            [
                {
                    "allowed": False,
                    "user_used": 3,
                    "daily_used": 3,
                    "total_used": 8,
                    "usage_date": "2026-09-11",
                    "denial_reason": "user_limit",
                }
            ]
        )
        client = SupabaseQuotaClient(
            supabase_url=VALID_SETTINGS["SUPABASE_URL"],
            secret_key=VALID_SETTINGS["SUPABASE_SECRET_KEY"],
        )

        decision = client.read_quota(
            user_key=self.user_key,
            config=self.config,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.user_remaining, 0)

    @patch("public_analysis._HTTPS_OPENER.open")
    def test_final_allowed_reservation_is_accepted(self, mocked_urlopen):
        mocked_urlopen.return_value = FakeResponse(
            [
                {
                    "allowed": True,
                    "user_used": 3,
                    "daily_used": 4,
                    "total_used": 9,
                    "usage_date": "2026-09-11",
                    "denial_reason": None,
                }
            ]
        )
        client = SupabaseQuotaClient(
            supabase_url=VALID_SETTINGS["SUPABASE_URL"],
            secret_key=VALID_SETTINGS["SUPABASE_SECRET_KEY"],
        )

        decision = client.reserve_attempt(
            user_key=self.user_key,
            config=self.config,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.user_remaining, 0)

    @patch("public_analysis._HTTPS_OPENER.open")
    def test_full_read_response_cannot_claim_an_attempt_is_available(
        self,
        mocked_urlopen,
    ):
        mocked_urlopen.return_value = FakeResponse(
            [
                {
                    "allowed": True,
                    "user_used": 3,
                    "daily_used": 4,
                    "total_used": 9,
                    "usage_date": "2026-09-11",
                    "denial_reason": None,
                }
            ]
        )
        client = SupabaseQuotaClient(
            supabase_url=VALID_SETTINGS["SUPABASE_URL"],
            secret_key=VALID_SETTINGS["SUPABASE_SECRET_KEY"],
        )

        with self.assertRaises(QuotaServiceError):
            client.read_quota(user_key=self.user_key, config=self.config)

    @patch(
        "public_analysis._HTTPS_OPENER.open",
        side_effect=URLError("offline"),
    )
    def test_network_failure_fails_closed(self, mocked_urlopen):
        client = SupabaseQuotaClient(
            supabase_url=VALID_SETTINGS["SUPABASE_URL"],
            secret_key=VALID_SETTINGS["SUPABASE_SECRET_KEY"],
        )

        with self.assertRaisesRegex(QuotaServiceError, "temporarily unavailable"):
            client.reserve_attempt(user_key=self.user_key, config=self.config)


if __name__ == "__main__":
    unittest.main()
