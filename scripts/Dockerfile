FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    libgtk-3-0 libdbus-glib-1-2 libx11-xcb1 libxtst6 libasound2 \
    xvfb x11vnc fluxbox novnc websockify \
    && rm -rf /var/lib/apt/lists/*

# Install Camoufox + FastAPI
RUN pip3 install --no-cache-dir camoufox[geoip] playwright fastapi uvicorn

# Download browsers
RUN python3 -m camoufox fetch
RUN playwright install firefox

# Copy API script
COPY scripts/api.py /api.py

# Updated startup script
RUN cat > /start.sh << 'SCRIPT'
#!/bin/bash
set -e

rm -f /tmp/.X99-lock
rm -rf /tmp/.X11-unix

echo "Starting Xvfb..."
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
sleep 3

export DISPLAY=:99

echo "Starting fluxbox..."
fluxbox &
sleep 2

echo "Starting VNC server..."
x11vnc -display :99 -forever -shared -rfbport 5900 -nopw -bg

echo "Starting noVNC..."
websockify --web=/usr/share/novnc 6080 localhost:5900 &
sleep 2

echo "Starting Camoufox API..."
uvicorn api:app --host 0.0.0.0 --port 8000 &

echo "========================================="
echo "✅ Camoufox ready!"
echo "VNC: http://localhost:6080/vnc.html"
echo "API: http://localhost:8000/docs"
echo "========================================="

tail -f /dev/null
SCRIPT

RUN chmod +x /start.sh

WORKDIR /workspace
EXPOSE 6080 5900 8000

CMD ["/bin/bash", "/start.sh"]
