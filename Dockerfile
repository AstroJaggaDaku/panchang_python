FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    gcc \
    libglib2.0-0 \
    libgl1 \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV PORT=8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
