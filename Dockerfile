FROM python:3.10-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Expose the port
EXPOSE 8888

# Run the application
CMD ["uvicorn", "src.scheduler.rostering_api:api", "--host", "0.0.0.0", "--port", "8888"]