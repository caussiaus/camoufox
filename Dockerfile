FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libasound2 \
    libx11-xcb1 \
    libxtst6 \
    fonts-liberation \
    xvfb \
    x11vnc \
    websockify \
    novnc \
    && rm -rf /var/lib/apt/lists/*

# Install Camoufox
RUN pip3 install camoufox[geoip]
RUN camoufox fetch

WORKDIR /workspace

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy application files
COPY agent_server.py .
COPY start.sh .
RUN chmod +x start.sh

# Create screenshots directory
RUN mkdir -p screenshots

CMD ["./start.sh"]
