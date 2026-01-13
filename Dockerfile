FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tzdata \
    ca-certificates \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Swiss Ephemeris data
RUN mkdir -p /usr/share/ephe && \
    wget -q https://www.astro.com/ftp/swisseph/ephe/sepl_18.se1 -O /usr/share/ephe/sepl_18.se1 && \
    wget -q https://www.astro.com/ftp/swisseph/ephe/semo_18.se1 -O /usr/share/ephe/semo_18.se1 && \
    wget -q https://www.astro.com/ftp/swisseph/ephe/seas_18.se1 -O /usr/share/ephe/seas_18.se1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

ENV SE_EPHE_PATH=/usr/share/ephe
ENV PORT=8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
