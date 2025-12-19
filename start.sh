#!/usr/bin/env bash
set -e

Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

x11vnc -display :99 -nopw -forever -shared -rfbport 5900 -listen 0.0.0.0 &
websockify --web=/usr/share/novnc 6080 localhost:5900 &

playwright install chromium --with-deps

python -u /workspace/agent_server.py
