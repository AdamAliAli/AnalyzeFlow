from copy import deepcopy
from app.services.ai.contract import AnalysisOutput


def inline_schema_refs(schema: dict) -> dict:
    definitions = schema.get("$defs", {})

    def expand(node):
        if isinstance(node, list):
            return [expand(item) for item in node]

        if not isinstance(node, dict):
            return node

        if "$ref" in node:
            reference = node["$ref"]
            prefix = "#/$defs/"

            if not reference.startswith(prefix):
                raise ValueError(f"Unsupported schema reference: {reference}")

            name = reference[len(prefix):]
            resolved = deepcopy(definitions[name])
            resolved.update({
                key: value
                for key, value in node.items()
                if key != "$ref"
            })
            return expand(resolved)

        return {
            key: expand(value)
            for key, value in node.items()
            if key != "$defs"
        }

    return expand(schema)

def build_analysis_tool() -> dict:                          # -> dict: means that this function returns a dictionary
    schema = inline_schema_refs(AnalysisOutput.model_json_schema())             # model_json_schema convert our Pydantic model (AnalysisOutput) to a JSON schema


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