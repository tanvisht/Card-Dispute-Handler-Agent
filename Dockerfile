FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[snowflake]"
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "dispute_triage.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
