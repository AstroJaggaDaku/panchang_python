FROM python:3.11-slim

# System deps + Swiss Ephemeris data
RUN apt-get update && apt-get install -y \
    swisseph-data \
    libsqlite3-0 \
    libgl1 \
    libglib2.0-0 \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Render exposes PORT, but Gunicorn listens on 8080 by default in Render
ENV PORT=8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
