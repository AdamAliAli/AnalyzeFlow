# AI integration

This document describes the implemented AI integration.

Provider used: OpenRouter

Why we chose it:

- It offers access to free model endpoints for our project testing.
- Each teammate can create their own API key. Whether a request is free depends on the selected model endpoint, not the key itself.

Model used: `nex-agi/nex-n2.5-mini:free`

## What we, the AI team, added

OpenRouter replaces the rule-based report generator when selected and successful. The deterministic evidence checks remain in use, and the existing mock analyzer remains available as a fallback. This integration does not change the database schema, scraper, HTTP routes, or job pipeline.

New files:

| File in `app/services/ai/` | Purpose |
| --- | --- |
| `openrouter_provider.py` | Sends the request to OpenRouter and translates request failures into `AnalyzerError`. |
| `prompts.py` | Defines evidence-grounding instructions and serializes the business/site input. |
| `tool_schema.py` | Builds the `submit_analysis` tool schema from `AnalysisOutput` and expands local schema references for endpoint compatibility. |
| `response_parser.py` | Extracts the tool response, rejects incomplete or invalid reports, and validates with Pydantic. |

Edited file:

- `registry.py`: Loads the OpenRouter provider so it can be selected through configuration.

## How to use it for the first time

Install the backend's existing dependencies and configure its database as described in the project's setup documentation. Add or update these values in your private `Backend/.env`:

```dotenv
AI_PROVIDER=openrouter
AI_MODEL=nex-agi/nex-n2.5-mini:free
AI_API_KEY=replace_with_your_own_openrouter_key
AI_TIMEOUT_SECONDS=240
AI_MAX_RETRIES=2
```

The 240-second timeout was used in our successful full-backend test. The repository default is 90 seconds; shorter timeouts may cut off slower responses. The timeout applies to each attempt, not the entire job.

You can change `AI_MODEL` to another OpenRouter model that supports our tool-calling request, including forcing the `submit_analysis` tool. Restart the backend and run a live check after changing it. Model availability and endpoint compatibility can vary.

Restart the backend after changing environment settings. Always keep `.env` and credentials out of Git. Anthropic is not implemented by this integration yet.

## How the report is produced

```text
Backend business details + website evidence
                    |
                    v
       Prompt + input JSON + tool schema
                    |
                    v
                OpenRouter (AI)
                    |
                    v
       Tool response -> parser -> validation
                    |
                    v
          Backend saves the report
```

The backend supplies business details and website evidence as an `AnalysisInput` object. We convert this input to JSON and send it with the instructions from `prompts.py` and the report's tool schema.

The provider uses OpenRouter's chat-completions endpoint with a forced `submit_analysis` function call. We use tool calling to request the report in the expected structure. This implementation does not use `response_format`.

The tool schema describes the expected report structure. The parser remains necessary: it checks that exactly one expected tool call was returned, decodes its arguments, and validates them against `AnalysisOutput`. A response cut short by the output limit is rejected. The parser sets `provider` to `openrouter` and `model` to the configured model identifier rather than trusting model-generated metadata; this is not the resolved upstream model version.

Prompts instruct the model to use supplied rule scores as a baseline, support findings with evidence, avoid invented site features or measured outcomes, leave unsupported framework answers null, and provide distinct, actionable recommendations.

We aim to cover visual, technical, and business findings. When evidence is insufficient, our prompt prioritizes avoiding invented findings and allows a category to remain empty. This is our interpretation of the original handoff's requirements to cover all three categories and avoid unsupported claims. Prompt instructions are not a guarantee of factual correctness; Pydantic validates structure and field constraints, not every claim.

## Retries and fallback

Retries belong to the existing backend pipeline, not the provider itself. `AI_MAX_RETRIES=2` allows up to three attempts in total for retryable errors. Non-retryable errors proceed to fallback without further AI attempts.

If AI analysis cannot complete, the pipeline generates a rule-based report tagged `mock-fallback`.

**A job marked `succeeded` does not prove AI success.** A fallback report can also finish successfully, with empty job error fields. Inspect the report's provider metadata and backend logs:

| Provider value | Meaning |
| --- | --- |
| `openrouter` | The OpenRouter response passed validation. |
| `mock-fallback` | AI failed and the pipeline used the rule-based report generator. |
| `mock` | The rule-based provider was selected directly, or the configured provider was not registered. |
