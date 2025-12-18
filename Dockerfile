FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# System deps: Firefox/Camoufox + Xvfb + VNC + noVNC
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-3-0 libdbus-glib-1-2 libxt6 libpci3 libasound2 libcups2 \
    libdbm2 libgmp10 libxcb1 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libxshmfence1 libxss1 libxst6 libns3 libnspr4 \
    ca-certificates fonts-liberation fonts-noto fonts-noto-color-emoji \
    curl wget \
    xvfb x11-utils x11vnc novnc websockify \
 && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /workspace
RUN mkdir -p /workspace/screenshots /workspace/logs

# Python deps
COPY requirements.txt .

# NOTE: prefer wheels and avoid re-resolving everything; this is where PyYAML blew up before. [file:1]
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --only-binary=:all: -r requirements.txt \
 && pip cache purge

# App files
COPY agent_server.py .
COPY start.sh .
RUN chmod +x /workspace/start.sh

EXPOSE 5555 6080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5555/health || exit 1

# Single entrypoint
CMD ["/workspace/start.sh"]
