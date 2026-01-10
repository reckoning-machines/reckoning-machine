from typing import Any, Tuple, Dict, Optional, List
from app.core.decision_rationale import validate_decision_rationale


def evaluate_policy(step: Any, output_json: Any, decision_rationale: Any) -> Tuple[str, Dict[str, Any]]:
    """
    Returns ("PASS"|"FAIL") and a deterministic execution policy report.
    """
    violations: List[Dict[str, Any]] = []

    ok_dr, dr_errors = validate_decision_rationale(decision_rationale)
    if not ok_dr:
        violations.append({"rule": "decision_rationale_valid", "outcome": "fail", "errors": dr_errors})

    if not isinstance(output_json, dict):
        violations.append({"rule": "output_json_is_object", "outcome": "fail", "detail": "output_json not a dict"})
    elif not output_json:
        violations.append({"rule": "output_json_non_empty", "outcome": "fail", "detail": "output_json empty"})

    if violations:
        return "FAIL", {"outcome": "FAIL", "violations": violations}

    return "PASS", {"outcome": "PASS", "violations": []}
