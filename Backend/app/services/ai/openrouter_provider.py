import asyncio

import httpx

from app.core.config import settings
from app.services.ai.contract import (
    AnalysisInput,
    AnalysisOutput,
    AnalyzerError,
)
from app.services.ai.prompts import SYSTEM_PROMPT, build_user_message
from app.services.ai.registry import register
from app.services.ai.response_parser import parse_analysis_response
from app.services.ai.tool_schema import build_analysis_tool


class OpenRouterAnalyzerProvider:
    name = "openrouter"

    async def analyze(self, payload: AnalysisInput) -> AnalysisOutput:
        api_key = settings.ai_api_key.strip()
        model = settings.ai_model.strip()

        if not api_key:
            raise AnalyzerError(
                "OpenRouter API key is missing.",
                retryable=False,
            )

        if not model:
            raise AnalyzerError(
                "OpenRouter model is missing.",
                retryable=False,
            )

        request_body = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_user_message(payload),
                },
            ],
            "tools": [build_analysis_tool()],
            "tool_choice": {
                "type": "function",
                "function": {"name": "submit_analysis"},
            },
            "provider": {"require_parameters": True},
            "max_tokens": 4096,
            "stream": False,
        }

        try:
            async with asyncio.timeout(settings.ai_timeout_seconds):
                async with httpx.AsyncClient(
                    timeout=settings.ai_timeout_seconds,
                ) as client:
                    response = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                        },
                        json=request_body,
                    )

            response.raise_for_status()

        except (TimeoutError, httpx.TimeoutException) as exc:
            raise AnalyzerError(
                "OpenRouter request timed out.",
                retryable=True,
            ) from exc

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise AnalyzerError(
                f"OpenRouter returned HTTP {status}.",
                retryable=status in (408, 429) or status >= 500,
            ) from exc

        except httpx.RequestError as exc:
            raise AnalyzerError(
                "Could not communicate with OpenRouter.",
                retryable=True,
            ) from exc

        try:
            response_data = response.json()
        except ValueError as exc:
            raise AnalyzerError(
                "OpenRouter returned an unreadable JSON response.",
                retryable=True,
            ) from exc

        return parse_analysis_response(response_data, model=model)

register("openrouter", OpenRouterAnalyzerProvider)