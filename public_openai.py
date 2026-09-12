"""Constrained OpenAI workflow used by the authenticated public demo."""

from agents import ModelSettings, RunConfig, Runner
from openai import AsyncOpenAI

from agent_core import build_analysis_request, create_job_match_agent
from public_analysis import PublicAnalysisConfig
from report_validation import validate_job_match_report


class PublicInputRejectedError(ValueError):
    """Raised when OpenAI's safety screening rejects submitted text."""


public_agent = create_job_match_agent(save_to_file=False)


async def run_public_openai_analysis(
    *,
    resume: str,
    job_description: str,
    config: PublicAnalysisConfig,
    safety_identifier: str,
) -> str:
    """Screen, analyze, and validate one public submission."""

    moderation_input = f"RESUME:\n{resume}\n\nJOB DESCRIPTION:\n{job_description}"
    moderation_client = AsyncOpenAI(
        api_key=config.openai_api_key,
        timeout=30.0,
    )

    try:
        moderation = await moderation_client.moderations.create(
            model="omni-moderation-latest",
            input=moderation_input,
        )
    finally:
        await moderation_client.close()

    if len(moderation.results) != 1:
        raise RuntimeError("OpenAI safety screening returned an invalid result.")

    if moderation.results[0].flagged:
        raise PublicInputRejectedError(
            "The submitted text could not be processed by the public demo."
        )

    analysis_request = build_analysis_request(
        resume=resume,
        job_description=job_description,
    )
    run_config = RunConfig(
        model_settings=ModelSettings(
            max_tokens=config.max_output_tokens,
            store=False,
            timeout=90.0,
            extra_args={"safety_identifier": safety_identifier},
        ),
        tracing_disabled=True,
        trace_include_sensitive_data=False,
        workflow_name="Public job match analysis",
    )
    result = await Runner.run(
        public_agent,
        analysis_request,
        max_turns=1,
        run_config=run_config,
    )
    return validate_job_match_report(result.final_output)
