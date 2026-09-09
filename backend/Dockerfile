FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies. Sentiment uses VADER only (settings.use_finbert=False), so
# torch + transformers + the FinBERT model download are intentionally omitted — this keeps
# the image small and the runtime footprint under 2 GB (t4g.small). To enable FinBERT,
# re-add `transformers` to requirements.txt and `pip install torch --index-url .../whl/cpu`.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
