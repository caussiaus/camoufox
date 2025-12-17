FROM python:3.11-slim

# Install system dependencies for Firefox
RUN apt-get update && apt-get install -y \
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libasound2 \
    libx11-xcb1 \
    libxtst6 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install Camoufox Python package
RUN pip3 install camoufox[geoip]

# Pre-download Camoufox browser
RUN camoufox fetch

WORKDIR /workspace
