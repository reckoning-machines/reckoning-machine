def stub_llm(prompt: str) -> dict:
    """
    Deterministic stub LLM adapter.
    Returns a fixed decision_rationale and output_json.
    """
    return {
        "decision_rationale": {
            "version": "v1",
            "summary": "stubbed rationale",
            "inputs_used": [],
            "assumptions": []
        },
        "output_json": {
            "result": "stubbed"
        }
    }
