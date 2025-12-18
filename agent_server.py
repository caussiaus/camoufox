#!/usr/bin/env python3
"""
Camoufox + browser-use Vision Agent
Qwen2.5-VL controls Camoufox browser via streaming agent
"""

import os
import json
import base64
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify, Response
from camoufox.sync_api import Camoufox
import ollama
from browser_use import Agent, BrowserConfig  # ← NEW
from browser_use.models import OllamaModel  # ← NEW
from ollama import Client

app = Flask(__name__)

# Config
OLLAMA_BASE = os.getenv('OLLAMA_BASE', 'http://ollama:11434')
VISION_MODEL = "redule26/huihui_ai_qwen2.5-vl-7b-abliterated:latest"
CAMOUFOX_VISUAL = os.getenv('CAMOUFOX_VISUAL', 'false').lower() == 'true'
HEADLESS = not CAMOUFOX_VISUAL

client = Client(host=OLLAMA_BASE)

class CamoufoxVisionAgent:
    def __init__(self):
        self.model = OllamaModel(
            model=VISION_MODEL,
            base_url=OLLAMA_BASE,
            api_key="ollama"  # dummy key for local
        )
        
    def create_browser_config(self):
        return BrowserConfig(
            headless=HEADLESS,
            window_size={"width": 1920, "height": 1080},
            timeout=60000,
            wait_for_network_idle=True,
            browser_type="firefox"  # Camoufox is Firefox-based
        )
    
    async def run_agent(self, url, task, stream=False):
        """Run browser-use agent with Camoufox"""
        try:
            # Custom browser launcher for Camoufox
            async def launch_browser():
                browser = Camoufox(headless=HEADLESS, humanize=True)
                return browser  # browser-use expects this pattern
            
            agent = Agent(
                model=self.model,
                browser_config=self.create_browser_config(),
                system_prompt=f"You are extracting disaster information. Task: {task}",
                max_steps=15
            )
            
            result = await agent.run_async(url=url, stream=stream)
            return {
                "status": "ok",
                "success": True,
                "extracted_data": result,
                "steps_taken": agent.steps_taken,
                "browser": "camoufox-browser-use"
            }
            
        except Exception as e:
            return {"status": "fail", "error": str(e)}

agent = CamoufoxVisionAgent()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'camoufox-browser-use-agent',
        'vision_model': VISION_MODEL,
        'browser_use': True,
        'headless': HEADLESS,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/scrape', methods=['POST'])
async def scrape():
    data = request.json or {}
    url = data.get('url')
    task = data.get('task', data.get('user_question', 'Extract information'))
    
    if not url:
        return jsonify({'error': 'Missing url'}), 400
    
    print(f"🚀 browser-use agent starting: {url} | Task: {task[:50]}")
    
    # Run agent
    result = await agent.run_agent(url, task)
    
    return jsonify(result)

@app.route('/stream/<task_id>', methods=['GET'])
async def stream_browser(task_id):
    """Stream browser session to chat UI (future)"""
    # SSE stream for real-time browser updates
    def generate():
        yield f"data: {json.dumps({'task_id': task_id, 'status': 'streaming'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    print("🦊 Camoufox + browser-use Vision Agent")
    print(f"Vision: {VISION_MODEL}")
    print(f"Browser: Camoufox (HEADLESS={HEADLESS})")
    print(f"Stream ready: http://0.0.0.0:5555")
    app.run(host='0.0.0.0', port=5555, debug=False)
