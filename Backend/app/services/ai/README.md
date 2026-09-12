# AI integration — what you need to build

Everything the backend needs from the AI side is one class with one method.
You do not touch the database, the HTTP layer, the scraper, or the job queue.

## The contract

Read `contract.py`. It defines:

- **`AnalysisInput`** — what you receive. Business context from the wizard,
  plus everything we measured on the live site (`SiteEvidence`), including
  `rule_signals`: deterministic checks the backend already ran.
- **`AnalysisOutput`** — what you must return. Scores, an executive summary,
  the five framework answers, findings, and recommendations.
- **`AnalyzerProvider`** — the protocol: `async def analyze(payload) -> AnalysisOutput`.
- **`AnalyzerError`** — raise this on failure. Set `retryable=False` for a bad
  API key or malformed request; `True` for timeouts and rate limits.

Both models are Pydantic, so you can hand `AnalysisOutput.model_json_schema()`
straight to a structured-output / tool-calling API and validate the reply with
`AnalysisOutput.model_validate_json(raw)`.

## Steps

1. Create `app/services/ai/openai_provider.py` (or `anthropic_provider.py` —
   both names are auto-imported if present).
2. Implement the class:

```python
from app.services.ai.contract import (
    AnalysisInput, AnalysisOutput, AnalyzerError,
)
from app.services.ai.registry import register


class OpenAIAnalyzerProvider:
    name = "openai"

    async def analyze(self, payload: AnalysisInput) -> AnalysisOutput:
        ...  # your call here
        return AnalysisOutput.model_validate_json(raw_json)


register("openai", OpenAIAnalyzerProvider)
```

3. Set `AI_PROVIDER=openai`, `AI_API_KEY=...`, `AI_MODEL=...` in `.env`.

That's it. The pipeline picks it up on the next request.

## Rules the backend enforces on your output

- A finding with neither `evidence` nor `description` is dropped.
- Recommendations are re-sorted by `priority` (1 = first).
- Scores must be 0–100. `rule_scores` in the input is your baseline — deviate
  from it when you have a reason, but a wildly different score with no
  supporting findings will look wrong next to the evidence list.
- Never invent facts about the site. If `SiteEvidence` doesn't support a
  claim, leave the field `None`. Empty is better than fabricated — the whole
  product promise is that the report is grounded in the real page.

## Failure behaviour (already handled, for your awareness)

If your provider raises, the pipeline retries per `AI_MAX_RETRIES`, then falls
back to the mock rule-based analyzer so the user still gets a report. Failures
are recorded on the job row with `error_code` / `error_message`.

## Testing without touching the API

`AI_PROVIDER=mock` (the default) runs the deterministic rule engine. Use it to
develop against a working end-to-end flow, then switch the env var.
