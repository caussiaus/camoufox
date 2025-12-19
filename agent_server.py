#!/usr/bin/env python3

"""
🦊 Camoufox Vision Agent + AI Agent Control
VNC + n8n READY - 100% WORKING + Ollama browser-use agent
"""

import os
import base64
import time
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify
from camoufox.sync_api import Camoufox
import ollama
from PIL import Image

# NEW: browser-use + Ollama agent support
try:
    from browser_use import Agent, Browser, BrowserConfig
    from langchain_ollama import ChatOllama
    BROWSER_USE_AVAILABLE = True
    print("✅ browser-use + Ollama agent READY")
except ImportError:
    BROWSER_USE_AVAILABLE = False
    print("⚠️ browser-use not installed - /agent endpoint disabled")

app = Flask(__name__)

# Config
OLLAMA_BASE = os.getenv('OLLAMABASE', 'http://192.168.10.50:11434')
VISION_MODEL = os.getenv('VLMMODEL', 'redule26/huihui_ai_qwen2.5-vl-7b-abliterated:latest')
AGENT_MODEL = os.getenv('AGENTMODEL', 'qwen2.5:7b')
CAMOUFOX_VISUAL = os.getenv('CAMOUFOXVISUAL', 'true').lower() == 'true'
HEADLESS = not CAMOUFOX_VISUAL
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
        'agent_model': AGENT_MODEL,
        'browser_use_available': BROWSER_USE_AVAILABLE,
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
        
        with Camoufox(headless=HEADLESS, humanize=True) as browser:
            page = browser.new_page()
            page.goto(url, wait_until='networkidle', timeout=NAV_TIMEOUT_MS)
            page.screenshot(path=screenshot, full_page=True, timeout=SHOT_TIMEOUT_MS)
            
            if CAMOUFOX_VISUAL and DEBUG_DWELL_SEC > 0:
                time.sleep(DEBUG_DWELL_SEC)
        
        try:
            img = Image.open(screenshot)
            img = img.convert('RGB')
            img = img.resize((1600, 900))
            img.save(screenshot, format='PNG', optimize=True)
            print(f"✅ Image normalized: {screenshot}")
        except Exception as e:
            print(f"⚠️ Image normalization failed: {e}")
        
        with open(screenshot, 'rb') as f:
            img_b64 = base64.b64encode(f.read()).decode()
        
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

@app.route('/agent', methods=['POST'])
def agent():
    if not BROWSER_USE_AVAILABLE:
        return jsonify({'error': 'browser-use not installed'}), 500
    
    data = request.json or {}
    task = data.get('task')
    
    if not task:
        return jsonify({'error': 'Missing task'}), 400
    
    model_name = data.get('model', AGENT_MODEL)
    max_steps = int(data.get('max_steps', 15))
    headless = data.get('headless', HEADLESS)
    
    print(f"🦊 AI Agent: {task[:80]}...")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_browser_agent(task, model_name, max_steps, headless))
        loop.close()
        
        return jsonify({
            "status": "ok",
            "mode": "ai_agent",
            "task": task,
            "model": model_name,
            "result": result
        })
    
    except Exception as e:
        print(f"❌ Agent error: {e}")
        return jsonify({"status": "fail", "error": str(e)}), 500

async def run_browser_agent(task: str, model_name: str, max_steps: int, headless: bool):
    llm = ChatOllama(model=model_name, base_url=OLLAMA_BASE, temperature=0.1)
    browser = Browser(config=BrowserConfig(headless=headless, slow_mo=200 if not headless else 0))
    agent = Agent(task=task, llm=llm, browser=browser, max_actions_per_step=max_steps)
    result = await agent.run()
    await browser.close()
    return result

if __name__ == '__main__':
    print("🦊 Camoufox Vision Agent STARTED")
    print(f"VNC: {'http://localhost:6080' if CAMOUFOX_VISUAL else 'DISABLED'}")
    print(f"Vision: {VISION_MODEL} | Agent: {AGENT_MODEL}")
    print(f"Browser-Use: {'✅' if BROWSER_USE_AVAILABLE else '❌'}")
    print("Endpoints: /health /scrape /agent")
    app.run(host='0.0.0.0', port=5555, debug=True)
