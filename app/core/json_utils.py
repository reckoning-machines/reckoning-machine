import json

def safe_json_loads(text):
    try:
        return json.loads(text), None
    except Exception as e:
        return None, str(e)
