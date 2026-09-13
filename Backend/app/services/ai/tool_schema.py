from app.services.ai.contract import AnalysisOutput


def build_analysis_tool() -> dict:                          # -> dict: means that this function returns a dictionary
    schema = AnalysisOutput.model_json_schema()              # model_json_schema convert our Pydantic model (AnalysisOutput) to a JSON schema


    schema["properties"].pop("provider", None)                 # .pop extract provider and model from the json that
    schema["properties"].pop("model", None)                         # we just converted

    return {
        "type": "function",
        "function": {                                            # This whole dictionary that we return is the format that OpenRouter (our provider)
            "name": "submit_analysis",                                    # expect to get
            "description": (
                "Return a website analysis grounded in the supplied "
                "business context and website evidence."
            ),
            "parameters": schema,
        },
    }