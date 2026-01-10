from typing import Any, Tuple, List


def validate_decision_rationale(obj: Any) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    if not isinstance(obj, dict):
        return False, ["Decision Rationale must be a JSON object"]

    version = obj.get("version")
    if not isinstance(version, str) or not version.strip():
        errors.append("Missing or invalid 'version' (must be non-empty string)")

    # Optional fields
    if "summary" in obj and obj["summary"] is not None and not isinstance(obj["summary"], str):
        errors.append("'summary' must be a string if present")

    if "nodes" in obj and obj["nodes"] is not None and not isinstance(obj["nodes"], list):
        errors.append("'nodes' must be a list if present")

    if "selected_path" in obj and obj["selected_path"] is not None and not isinstance(obj["selected_path"], list):
        errors.append("'selected_path' must be a list if present")

    return (len(errors) == 0), errors
