#!/usr/bin/env bash
set -e

# 1) Virtual X display
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

# 2) VNC server on :99
x11vnc -display :99 -nopw -forever -shared -rfbport 5900 -listen 0.0.0.0 &

# 3) noVNC websockify -> 6080
websockify --web=/usr/share/novnc 6080 localhost:5900 &

# 4) Start Camoufox agent
python -u /workspace/agent_server.py
