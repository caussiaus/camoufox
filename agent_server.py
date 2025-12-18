#!/usr/bin/env python3
"""
🦊 Camoufox Vision Agent - CLEAN NO browser-use
VNC + n8n READY - 100% WORKING
Image normalization for stability + timeouts
"""

import os
import base64
import time
from datetime import datetime

from flask import Flask, request, jsonify
from camoufox.sync_api import Camoufox
import ollama
from PIL import Image

app = Flask(__name__)

# Config
OLLAMA_BASE = os.getenv('OLLAMABASE', 'http://192.168.10.50:11434')
VISION_MODEL = os.getenv('VLMMODEL', 'redule26/huihui_ai_qwen2.5-vl-7b-abliterated:latest')
CAMOUFOX_VISUAL = os.getenv('CAMOUFOXVISUAL', 'true').lower() == 'true'
HEADLESS = not CAMOUFOX_VISUAL

# Tuning knobs (set via env or use defaults)
NAV_TIMEOUT_MS = int(os.getenv('NAV_TIMEOUT_MS', '60000'))
SHOT_TIMEOUT_MS = int(os.getenv('SHOT_TIMEOUT_MS', '60000'))
DEBUG_DWELL_SEC = int(os.getenv('DEBUG_DWELL_SEC', '2'))

client = ollama.Client(host=OLLAMA_BASE)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'camoufox-vision-agent',
        'vnc_enabled': CAMOUFOX_VISUAL,
        'headless': HEADLESS,
        'vision_model': VISION_MODEL,
        'nav_timeout_ms': NAV_TIMEOUT_MS,
        'debug_dwell_sec': DEBUG_DWELL_SEC,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.json or {}
    url = data.get('url')
    task = data.get('task', 'Extract information')
    
    if not url:
        return jsonify({'error': 'Missing url'}), 400
    
    print(f"🦊 Scraping: {url}")
    
    try:
        ts = int(time.time())
        screenshot = f"/workspace/screenshots/{ts}.png"

        # Launch Camoufox (headed when CAMOUFOXVISUAL=true)
        with Camoufox(headless=HEADLESS, humanize=True) as browser:
            page = browser.new_page()
            
            # Navigate with explicit timeout
            page.goto(url, wait_until='networkidle', timeout=NAV_TIMEOUT_MS)
            
            # Screenshot with explicit timeout
            page.screenshot(path=screenshot, full_page=True, timeout=SHOT_TIMEOUT_MS)
            
            # Keep final state on screen briefly for VNC viewers (only in visual mode)
            if CAMOUFOX_VISUAL and DEBUG_DWELL_SEC > 0:
                time.sleep(DEBUG_DWELL_SEC)

        # Normalize image for stable vision model behavior
        try:
            img = Image.open(screenshot)
            img = img.convert('RGB')                    # ensure 3 channels
            img = img.resize((1600, 900))              # fixed resolution
            img.save(screenshot, format='PNG', optimize=True)
            print(f"✅ Image normalized: {screenshot}")
        except Exception as e:
            print(f"⚠️ Image normalization failed: {e} (continuing with original)")

        # Encode screenshot to base64
        with open(screenshot, 'rb') as f:
            img_b64 = base64.b64encode(f.read()).decode()
        
        # Send to vision model
        response = client.generate(
            model=VISION_MODEL,
            prompt=f"Analyze screenshot for task: {task}",
            images=[img_b64]
        )
        
        return jsonify({
            "status": "ok",
            "screenshot": screenshot,
            "analysis": response['response']
        })
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"status": "fail", "error": str(e)}), 500


if __name__ == '__main__':
    print("🦊 Camoufox Vision Agent STARTED")
    print(f"VNC: {'http://localhost:6080' if CAMOUFOX_VISUAL else 'DISABLED'}")
    print(f"Nav timeout: {NAV_TIMEOUT_MS}ms | Screenshot timeout: {SHOT_TIMEOUT_MS}ms | Debug dwell: {DEBUG_DWELL_SEC}s")
    app.run(host='0.0.0.0', port=5555, debug=True)
