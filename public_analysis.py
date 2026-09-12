"""Security and quota helpers for the public OpenAI analysis flow."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

DEFAULT_USER_LIMIT = 3
DEFAULT_DAILY_LIMIT = 10
DEFAULT_TOTAL_LIMIT = 100
DEFAULT_MAX_RESUME_CHARACTERS = 8_000
DEFAULT_MAX_JOB_CHARACTERS = 8_000
DEFAULT_MAX_OUTPUT_TOKENS = 3_000
MIN_INPUT_CHARACTERS = 100

TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off", ""}


class _NoRedirectHandler(HTTPRedirectHandler):
    """Keep server credentials on the validated Supabase origin."""

    def redirect_request(self, request, file_pointer, code, message, headers, url):
        return None


_HTTPS_OPENER = build_opener(_NoRedirectHandler())


class PublicAnalysisConfigurationError(ValueError):
    """Raised when public-analysis settings are invalid."""


class QuotaServiceError(RuntimeError):
    """Raised when the persistent quota service cannot be used safely."""


@dataclass(frozen=True)
class PublicAnalysisConfig:
    """Validated settings for the limited public analysis feature."""

    enabled: bool
    user_limit: int
    daily_limit: int
    total_limit: int
    max_resume_characters: int
    max_job_characters: int
    max_output_tokens: int
    supabase_url: str
    supabase_secret_key: str = field(repr=False)
    user_hash_salt: str = field(repr=False)
    openai_api_key: str = field(repr=False)

    @property
    def missing_secret_names(self) -> tuple[str, ...]:
        """Return required secret names that are not configured."""

        if not self.enabled:
            return ()

        values = {
            "OPENAI_API_KEY": self.openai_api_key,
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_SECRET_KEY": self.supabase_secret_key,
            "USER_HASH_SALT": self.user_hash_salt,
        }
        return tuple(name for name, value in values.items() if not value.strip())

    @property
    def is_ready(self) -> bool:
        """Return whether the enabled feature has every required secret."""

        return self.enabled and not self.missing_secret_names


@dataclass(frozen=True)
class QuotaDecision:
    """One persistent quota read or reservation result."""

    allowed: bool
    user_used: int
    daily_used: int
    total_used: int
    user_limit: int
    daily_limit: int
    total_limit: int
    usage_date: str
    denial_reason: str | None = None

    @property
    def user_remaining(self) -> int:
        """Return the number of analysis attempts left for this account."""

        return max(self.user_limit - self.user_used, 0)


def _parse_bool(name: str, raw_value: str) -> bool:
    normalized = raw_value.strip().lower()

    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False

    raise PublicAnalysisConfigurationError(f"{name} must be true or false.")


def _parse_int(
    settings: Mapping[str, str],
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    raw_value = settings.get(name, str(default)).strip()

    try:
        value = int(raw_value)
    except ValueError as error:
        raise PublicAnalysisConfigurationError(
            f"{name} must be a whole number."
        ) from error

    if not minimum <= value <= maximum:
        raise PublicAnalysisConfigurationError(
            f"{name} must be between {minimum} and {maximum}."
        )

    return value


def load_public_analysis_config(
    settings: Mapping[str, str] | None = None,
) -> PublicAnalysisConfig:
    """Read and validate public-analysis configuration.

    The feature is disabled by default. Invalid limits fail closed instead of
    silently allowing unmetered OpenAI requests.
    """

    values = os.environ if settings is None else settings
    enabled = _parse_bool(
        "ENABLE_PUBLIC_OPENAI_ANALYSIS",
        values.get("ENABLE_PUBLIC_OPENAI_ANALYSIS", "false"),
    )
    user_limit = _parse_int(
        values,
        "PUBLIC_ANALYSIS_USER_LIMIT",
        DEFAULT_USER_LIMIT,
        minimum=1,
        maximum=10,
    )
    daily_limit = _parse_int(
        values,
        "PUBLIC_ANALYSIS_DAILY_LIMIT",
        DEFAULT_DAILY_LIMIT,
        minimum=1,
        maximum=1_000,
    )
    total_limit = _parse_int(
        values,
        "PUBLIC_ANALYSIS_TOTAL_LIMIT",
        DEFAULT_TOTAL_LIMIT,
        minimum=1,
        maximum=100_000,
    )

    if user_limit > total_limit or daily_limit > total_limit:
        raise PublicAnalysisConfigurationError(
            "The total analysis limit must be at least as large as the user "
            "and daily limits."
        )

    user_hash_salt = values.get("USER_HASH_SALT", "").strip()

    if enabled and user_hash_salt and len(user_hash_salt) < 32:
        raise PublicAnalysisConfigurationError(
            "USER_HASH_SALT must contain at least 32 characters."
        )

    return PublicAnalysisConfig(
        enabled=enabled,
        user_limit=user_limit,
        daily_limit=daily_limit,
        total_limit=total_limit,
        max_resume_characters=_parse_int(
            values,
            "PUBLIC_MAX_RESUME_CHARACTERS",
            DEFAULT_MAX_RESUME_CHARACTERS,
            minimum=1_000,
            maximum=20_000,
        ),
        max_job_characters=_parse_int(
            values,
            "PUBLIC_MAX_JOB_CHARACTERS",
            DEFAULT_MAX_JOB_CHARACTERS,
            minimum=1_000,
            maximum=20_000,
        ),
        max_output_tokens=_parse_int(
            values,
            "PUBLIC_MAX_OUTPUT_TOKENS",
            DEFAULT_MAX_OUTPUT_TOKENS,
            minimum=500,
            maximum=5_000,
        ),
        supabase_url=values.get("SUPABASE_URL", "").strip(),
        supabase_secret_key=values.get("SUPABASE_SECRET_KEY", "").strip(),
        user_hash_salt=user_hash_salt,
        openai_api_key=values.get("OPENAI_API_KEY", "").strip(),
    )


def build_private_user_key(*, issuer: str, subject: str, salt: str) -> str:
    """Create a stable pseudonymous key without storing identity claims."""

    clean_issuer = issuer.strip()
    clean_subject = subject.strip()
    clean_salt = salt.strip()

    if not clean_issuer or not clean_subject or not clean_salt:
        raise ValueError("Issuer, subject, and salt are required.")

    identity = f"{clean_issuer}\x1f{clean_subject}".encode()
    return hmac.new(
        clean_salt.encode(),
        identity,
        hashlib.sha256,
    ).hexdigest()


def build_safety_identifier(user_key: str) -> str:
    """Create the privacy-preserving identifier sent with OpenAI requests."""

    if len(user_key) != 64 or any(
        character not in "0123456789abcdef" for character in user_key
    ):
        raise ValueError("The user key must be a SHA-256 hexadecimal digest.")

    return f"job_match_{user_key[:48]}"


def auth_settings_are_valid(settings: Mapping[str, Any]) -> bool:
    """Validate the required Streamlit Google OIDC configuration."""

    required_names = (
        "redirect_uri",
        "cookie_secret",
        "client_id",
        "client_secret",
        "server_metadata_url",
    )

    if not all(str(settings.get(name, "")).strip() for name in required_names):
        return False

    redirect_uri = str(settings["redirect_uri"]).strip()
    parsed_redirect = urlsplit(redirect_uri)
    is_local_redirect = (
        parsed_redirect.scheme == "http"
        and parsed_redirect.hostname in {"localhost", "127.0.0.1"}
    )
    is_secure_redirect = parsed_redirect.scheme == "https"

    return (
        (is_local_redirect or is_secure_redirect)
        and parsed_redirect.hostname is not None
        and parsed_redirect.path == "/oauth2callback"
        and not parsed_redirect.query
        and not parsed_redirect.fragment
        and len(str(settings["cookie_secret"]).strip()) >= 32
        and str(settings["server_metadata_url"]).strip()
        == "https://accounts.google.com/.well-known/openid-configuration"
    )


def validate_public_inputs(
    *,
    resume: str,
    job_description: str,
    config: PublicAnalysisConfig,
) -> str | None:
    """Return a public-safe validation message, or None when inputs are valid."""

    clean_resume = resume.strip()
    clean_job = job_description.strip()

    if not clean_resume or not clean_job:
        return "Please provide both a resume and a job description."
    if len(clean_resume) < MIN_INPUT_CHARACTERS:
        return "Please provide a more complete resume before running the analysis."
    if len(clean_job) < MIN_INPUT_CHARACTERS:
        return (
            "Please provide a more complete job description before running "
            "the analysis."
        )
    if len(resume) > config.max_resume_characters:
        return "The resume is longer than the public analysis limit."
    if len(job_description) > config.max_job_characters:
        return "The job description is longer than the public analysis limit."

    return None


class SupabaseQuotaClient:
    """Call atomic quota functions through Supabase's server-side Data API."""

    def __init__(
        self,
        *,
        supabase_url: str,
        secret_key: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        parsed_url = urlsplit(supabase_url)

        hostname = parsed_url.hostname or ""

        if (
            parsed_url.scheme != "https"
            or not hostname.endswith(".supabase.co")
            or parsed_url.username is not None
            or parsed_url.password is not None
            or parsed_url.path not in ("", "/")
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise PublicAnalysisConfigurationError(
                "SUPABASE_URL must be a complete Supabase HTTPS URL."
            )
        if not secret_key.strip():
            raise PublicAnalysisConfigurationError("SUPABASE_SECRET_KEY is required.")

        self._supabase_url = supabase_url.rstrip("/")
        self._secret_key = secret_key.strip()
        self._timeout_seconds = timeout_seconds

    def read_quota(
        self,
        *,
        user_key: str,
        config: PublicAnalysisConfig,
    ) -> QuotaDecision:
        """Read the current quota without consuming an attempt."""

        payload = self._quota_payload(user_key=user_key, config=config)
        return self._rpc("read_public_analysis_quota", payload, config)

    def reserve_attempt(
        self,
        *,
        user_key: str,
        config: PublicAnalysisConfig,
    ) -> QuotaDecision:
        """Atomically reserve one API attempt if every limit permits it."""

        payload = self._quota_payload(user_key=user_key, config=config)
        return self._rpc("reserve_public_analysis", payload, config)

    @staticmethod
    def _quota_payload(
        *,
        user_key: str,
        config: PublicAnalysisConfig,
    ) -> dict[str, object]:
        return {
            "p_user_key": user_key,
            "p_user_limit": config.user_limit,
            "p_daily_limit": config.daily_limit,
            "p_total_limit": config.total_limit,
        }

    def _rpc(
        self,
        function_name: str,
        payload: dict[str, object],
        config: PublicAnalysisConfig,
    ) -> QuotaDecision:
        endpoint = f"{self._supabase_url}/rest/v1/rpc/{function_name}"
        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "apikey": self._secret_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "job-match-agent-server/1.0",
            },
            method="POST",
        )

        try:
            with _HTTPS_OPENER.open(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                response_body = response.read(16_385)

                if len(response_body) > 16_384:
                    raise QuotaServiceError(
                        "The usage-limit service returned an invalid response."
                    )

                result = json.loads(response_body.decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise QuotaServiceError(
                "The usage-limit service is temporarily unavailable."
            ) from error

        if isinstance(result, list) and len(result) == 1:
            record = result[0]
        elif isinstance(result, dict):
            record = result
        else:
            raise QuotaServiceError(
                "The usage-limit service returned an invalid response."
            )

        if not isinstance(record, dict):
            raise QuotaServiceError(
                "The usage-limit service returned an invalid response."
            )

        try:
            allowed_value = record["allowed"]

            if not isinstance(allowed_value, bool):
                raise TypeError("The allowed value must be boolean.")

            decision = QuotaDecision(
                allowed=allowed_value,
                user_used=self._non_negative_int(record["user_used"]),
                daily_used=self._non_negative_int(record["daily_used"]),
                total_used=self._non_negative_int(record["total_used"]),
                user_limit=config.user_limit,
                daily_limit=config.daily_limit,
                total_limit=config.total_limit,
                usage_date=str(record["usage_date"]),
                denial_reason=(
                    str(record["denial_reason"])
                    if record.get("denial_reason")
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise QuotaServiceError(
                "The usage-limit service returned an invalid response."
            ) from error

        try:
            date.fromisoformat(decision.usage_date)
        except ValueError as error:
            raise QuotaServiceError(
                "The usage-limit service returned an invalid response."
            ) from error

        if decision.total_used >= config.total_limit:
            reached_limit_reason = "total_limit"
        elif decision.daily_used >= config.daily_limit:
            reached_limit_reason = "daily_limit"
        elif decision.user_used >= config.user_limit:
            reached_limit_reason = "user_limit"
        else:
            reached_limit_reason = None

        counters_exceed_limits = (
            decision.user_used > config.user_limit
            or decision.daily_used > config.daily_limit
            or decision.total_used > config.total_limit
        )
        is_reservation = function_name == "reserve_public_analysis"

        if decision.allowed:
            # A successful reservation returns counters *after* incrementing.
            # Therefore the final permitted attempt can legitimately return 3/3.
            allowed_response_is_invalid = (
                decision.denial_reason is not None
                or counters_exceed_limits
                or (not is_reservation and reached_limit_reason is not None)
                or (
                    is_reservation
                    and min(
                        decision.user_used,
                        decision.daily_used,
                        decision.total_used,
                    )
                    < 1
                )
            )
        else:
            allowed_response_is_invalid = (
                reached_limit_reason is None
                or decision.denial_reason != reached_limit_reason
            )

        if allowed_response_is_invalid:
            raise QuotaServiceError(
                "The usage-limit service returned an invalid response."
            )

        return decision

    @staticmethod
    def _non_negative_int(value: object) -> int:
        if isinstance(value, bool):
            raise TypeError("Boolean values are not valid counters.")

        if isinstance(value, int):
            integer = value
        elif isinstance(value, str) and value.isdigit():
            integer = int(value)
        else:
            raise ValueError("Counters must be whole numbers.")

        if integer < 0:
            raise ValueError("Counters cannot be negative.")

        return integer
