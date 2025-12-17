FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONUNBUFFERED=1

# Install system dependencies for Firefox
RUN apt-get update && apt-get install -y --no-install-recommends \
    firefox-esr \
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libxt6 \
    libpci3 \
    libasound2 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxshmfence1 \
    libxss1 \
    libxtst6 \
    libnss3 \
    libnspr4 \
    fonts-liberation \
    fonts-noto-color-emoji \
    fonts-noto-cjk \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Python dependencies
RUN pip install --no-cache-dir \
    playwright==1.48.0 \
    flask==3.0.0 \
    requests==2.31.0 \
    beautifulsoup4==4.12.3 \
    ollama==0.4.0

# Install ONLY Playwright Firefox browser (skip install-deps, we already have deps)
RUN playwright install firefox

WORKDIR /workspace

RUN mkdir -p /workspace/screenshots

COPY agent_server.py /workspace/

EXPOSE 5555

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5555/health || exit 1

CMD ["python", "-u", "agent_server.py"]
