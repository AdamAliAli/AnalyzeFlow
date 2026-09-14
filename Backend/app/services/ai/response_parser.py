import json

from pydantic import ValidationError

from app.services.ai.contract import AnalysisOutput, AnalyzerError


def parse_analysis_response(
    response: dict,
    model: str,
) -> AnalysisOutput:
    try:
        choice = response["choices"][0]

        if choice.get("finish_reason") == "length":
            raise AnalyzerError(
                "The model response was cut short.",
                retryable=True,
            )

        tool_calls = choice["message"].get("tool_calls", [])

        if len(tool_calls) != 1:
            raise AnalyzerError(
                "Expected exactly one report tool call.",
                retryable=True,
            )

        function = tool_calls[0]["function"]

        if function["name"] != "submit_analysis":
            raise AnalyzerError(
                "The model returned an unexpected tool call.",
                retryable=True,
            )

        report_data = json.loads(function["arguments"])

        if not isinstance(report_data, dict):
            raise AnalyzerError(
                "The report must be a JSON object.",
                retryable=True,
            )

        # Set these ourselves instead of trusting model-generated values.
        report_data["provider"] = "openrouter"
        report_data["model"] = model

        return AnalysisOutput.model_validate(report_data)

    except (
        KeyError,
        IndexError,
        TypeError,
        AttributeError,
        ValueError,
        ValidationError,
    ) as exc:
        raise AnalyzerError(
            "The model response did not match the report contract.",
            retryable=True,
        ) from exc