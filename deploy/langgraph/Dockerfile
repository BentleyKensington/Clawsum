FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY graphs graphs/
COPY server.py .

RUN pip install --no-cache-dir .

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ok')"

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
