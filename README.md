# Installation

`pip install -r requirements.txt`

# Testing

`pytest -s /tests`

# Enter venv

`source venv/bin/activate`

# Run server

`uvicorn src.scheduler.rostering_api:api --host 0.0.0.0 --port 8888 --reload`
