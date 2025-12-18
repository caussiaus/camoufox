FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# System dependencies for Camoufox + browser-use
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-3-0 libgconf-2-4 libdbus-glib-1-2 libxt6 libpci3 \
    libasound2 libcups2 libdrm2 libgbm1 libxcb1 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libxshmfence1 libxss1 libxtst6 \
    libnss3 libnspr4 ca-certificates \
    fonts-liberation fonts-noto-color-emoji fonts-noto-cjk \
    curl wget xvfb x11-utils novnc websockify \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

# Python dependencies
RUN pip install --no-cache-dir \
    camoufox==0.2.14 \
    browser-use==0.1.0 \
    flask==3.0.0 \
    ollama==0.4.0 \
    playwright==1.48.0 \
    websockets==13.0 \
    aiohttp==3.10.0 \
    tenacity==8.2.3 \
    requests==2.31.0

WORKDIR /workspace

RUN mkdir -p /workspace/screenshots /workspace/logs

COPY agent_server.py .

EXPOSE 5555 6080

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5555/health || exit 1

CMD ["python", "-u", "agent_server.py"]
