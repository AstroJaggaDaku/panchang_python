FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    wget \
    tzdata \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Swiss Ephemeris data from GitHub (Render allowed)
RUN mkdir -p /usr/share/ephe && \
    wget -q https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/sepl_18.se1 -O /usr/share/ephe/sepl_18.se1 && \
    wget -q https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/semo_18.se1 -O /usr/share/ephe/semo_18.se1 && \
    wget -q https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/seas_18.se1 -O /usr/share/ephe/seas_18.se1

# Tell Swiss Ephemeris where data is
ENV SE_EPHE_PATH=/usr/share/ephe

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV PORT=8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
