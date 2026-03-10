web: PYTHONPATH=backend:. uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: PYTHONPATH=backend:. python -m app.scheduler
