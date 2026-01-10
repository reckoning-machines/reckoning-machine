# Reckoning Machine

Stage A skeleton: FastAPI + static UI + health endpoint.

## Setup & Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open your browser to: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
