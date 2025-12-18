#!/usr/bin/env python3
"""
Modular Camoufox + browser-use Vision Agent
Controls via API params for n8n flexibility
Qwen2.5-VL drives browser actions with full visibility
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from flask import Flask, request, jsonify, Response
import time

# Camoufox + browser-use
from camoufox.sync_api import Camoufox
from browser_use import Agent, BrowserConfig
from browser_use.models import OllamaModel
from ollama import Client

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ============================================================================
# CONFIGURATION (ENV OVERRIDABLE)
# ============================================================================

DEFAULT_OLLAMA_BASE = os.getenv('OLLAMA_BASE', 'http://ollama:11434')
DEFAULT_VISION_MODEL = os.getenv('VLM_MODEL', 'redule26/huihui_ai_qwen2.5-vl-7b-abliterated:latest')
DEFAULT_TEXT_MODEL = os.getenv('TEXT_MODEL', 'qwen2.5:14b')
DEFAULT_BROWSER = os.getenv('BROWSER_TYPE', 'camoufox')
CAMOUFOX_VISUAL = os.getenv('CAMOUFOX_VISUAL', 'false').lower() == 'true'

client = Client(host=DEFAULT_OLLAMA_BASE)

# ============================================================================
# MODULAR VISION AGENT CLASS
# ============================================================================

class ModularVisionAgent:
    """
    Flexible agent supporting model/browser/prompt swapping via API params
    Perfect for n8n control
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        model_base: Optional[str] = None,
        browser_type: Optional[str] = None,
        headless: Optional[bool] = None,
        system_prompt: Optional[str] = None,
        max_steps: int = 15,
        request_id: str = "unknown"
    ):
        self.model_name = model_name or DEFAULT_VISION_MODEL
        self.model_base = model_base or DEFAULT_OLLAMA_BASE
        self.browser_type = browser_type or DEFAULT_BROWSER
        self.headless = headless if headless is not None else (not CAMOUFOX_VISUAL)
        self.system_prompt = system_prompt or "You are a web scraping assistant. Extract relevant information."
        self.max_steps = max_steps
        self.request_id = request_id
        self.start_time = time.time()
        
        logger.info(f"[{self.request_id}] 🔧 Agent initialized:")
        logger.info(f"   Model: {self.model_name}")
        logger.info(f"   Browser: {self.browser_type}")
        logger.info(f"   Headless: {self.headless}")
        logger.info(f"   Max steps: {self.max_steps}")
    
    def get_model(self) -> OllamaModel:
        """Get configured model client"""
        return OllamaModel(
            model=self.model_name,
            base_url=self.model_base,
            api_key="ollama"
        )
    
    def get_browser_config(self) -> BrowserConfig:
        """Get configured browser settings"""
        return BrowserConfig(
            headless=self.headless,
            window_size={"width": 1920, "height": 1080},
            timeout=60000,
            wait_for_network_idle=True,
            browser_type="firefox"  # Camoufox is Firefox-based
        )
    
    async def run(self, url: str, task: str) -> Dict[str, Any]:
        """
        Run agent with current config
        Returns structured result compatible with n8n
        """
        try:
            logger.info(f"[{self.request_id}] 🚀 Starting agent for {url[:60]}")
            logger.info(f"[{self.request_id}] 📋 Task: {task[:80]}")
            
            # Launch browser
            if self.browser_type == "camoufox":
                logger.info(f"[{self.request_id}] 🦊 Launching Camoufox (headless={self.headless})")
                browser = Camoufox(headless=self.headless, humanize=True)
            else:
                logger.error(f"[{self.request_id}] ❌ Unknown browser: {self.browser_type}")
                return self._error_response(f"Unknown browser: {self.browser_type}")
            
            # Create agent
            agent = Agent(
                model=self.get_model(),
                browser_config=self.get_browser_config(),
                system_prompt=f"{self.system_prompt}\n\nTask: {task}",
                max_steps=self.max_steps
            )
            
            # Run agent (browser-use does the heavy lifting)
            logger.info(f"[{self.request_id}] 🧠 Running browser-use agent...")
            result = await agent.run_async(url=url)
            
            execution_time = time.time() - self.start_time
            
            logger.info(f"[{self.request_id}] ✅ Agent success in {execution_time:.2f}s")
            
            return {
                "status": "ok",
                "success": True,
                "url": url,
                "task": task,
                "extracted_data": result,
                "metadata": {
                    "model": self.model_name,
                    "browser": self.browser_type,
                    "headless": self.headless,
                    "steps_taken": getattr(agent, 'steps_taken', 0),
                    "timestamp": datetime.now().isoformat(),
                    "request_id": self.request_id
                },
                "execution_time": execution_time
            }
            
        except Exception as e:
            logger.error(f"[{self.request_id}] ❌ Agent error: {str(e)}", exc_info=True)
            return self._error_response(str(e))
    
    def _error_response(self, error: str) -> Dict[str, Any]:
        """Build standardized error response"""
        execution_time = time.time() - self.start_time
        return {
            "status": "fail",
            "success": False,
            "error": error,
            "metadata": {
                "model": self.model_name,
                "browser": self.browser_type,
                "request_id": self.request_id
            },
            "execution_time": execution_time
        }

# ============================================================================
# FLASK API ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check with current configuration"""
    try:
        models = client.list()
        ollama_ok = models is not None
    except Exception as e:
        logger.warning(f"Ollama connection check failed: {e}")
        ollama_ok = False
    
    return jsonify({
        'status': 'healthy' if ollama_ok else 'degraded',
        'service': 'modular-camoufox-browser-use-agent',
        'defaults': {
            'vision_model': DEFAULT_VISION_MODEL,
            'text_model': DEFAULT_TEXT_MODEL,
            'browser': DEFAULT_BROWSER,
            'headless': not CAMOUFOX_VISUAL
        },
        'ollama_base': DEFAULT_OLLAMA_BASE,
        'ollama_connected': ollama_ok,
        'timestamp': datetime.now().isoformat(),
        'version': '2.1-modular-browser-use'
    }), (200 if ollama_ok else 503)


@app.route('/models', methods=['GET'])
def list_models():
    """List available Ollama models"""
    try:
        models_response = client.list()
        models = [m['name'] for m in models_response.get('models', [])]
        return jsonify({
            'status': 'ok',
            'models': models,
            'count': len(models),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return jsonify({'error': str(e), 'status': 'fail'}), 500


@app.route('/scrape', methods=['POST'])
async def scrape():
    """
    Main modular scraping endpoint
    """
    request_id = request.headers.get('X-Request-ID', f"req_{int(time.time() * 1000)}")
    
    try:
        data = request.json or {}
        
        # Required fields
        url = data.get('url')
        task = data.get('task') or data.get('user_question', 'Extract information')
        
        if not url:
            logger.warning(f"[{request_id}] ⚠️ Missing URL in request")
            return jsonify({'error': 'Missing required field: url', 'status': 'fail'}), 400
        
        # Optional overrides (n8n can control these)
        model_override = data.get('model')
        browser_override = data.get('browser')
        headless_override = data.get('headless')
        prompt_override = data.get('system_prompt')
        max_steps_override = data.get('max_steps', 15)
        
        logger.info(f"[{request_id}] 📥 Scrape request:")
        logger.info(f"   URL: {url[:60]}")
        logger.info(f"   Task: {task[:60]}")
        
        # Create agent with overrides
        agent = ModularVisionAgent(
            model_name=model_override,
            browser_type=browser_override,
            headless=headless_override,
            system_prompt=prompt_override,
            max_steps=max_steps_override,
            request_id=request_id
        )
        
        # Run agent
        result = await agent.run(url, task)
        
        if result.get('success'):
            logger.info(f"[{request_id}] ✅ Scrape completed successfully")
            return jsonify(result), 200
        else:
            logger.error(f"[{request_id}] ❌ Scrape failed: {result.get('error')}")
            return jsonify(result), 500
        
    except Exception as e:
        logger.exception(f"[{request_id}] ❌ Unhandled error in /scrape: {e}")
        return jsonify({
            'status': 'fail',
            'error': str(e),
            'request_id': request_id
        }), 500


@app.route('/config', methods=['GET'])
def get_config():
    """Return current default configuration"""
    return jsonify({
        'status': 'ok',
        'defaults': {
            'ollama_base': DEFAULT_OLLAMA_BASE,
            'vision_model': DEFAULT_VISION_MODEL,
            'text_model': DEFAULT_TEXT_MODEL,
            'browser': DEFAULT_BROWSER,
            'headless': not CAMOUFOX_VISUAL,
            'visual_mode': CAMOUFOX_VISUAL
        },
        'endpoints': {
            'health': 'GET /health',
            'models': 'GET /models',
            'config': 'GET /config',
            'scrape': 'POST /scrape (with model/browser/prompt overrides)',
        },
        'timestamp': datetime.now().isoformat()
    })


@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'status': 'error',
        'error': 'Endpoint not found',
        'available': [
            'GET /health',
            'GET /models',
            'GET /config',
            'POST /scrape'
        ]
    }), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({
        'status': 'error',
        'error': 'Internal server error'
    }), 500


# ============================================================================
# STARTUP
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("  🦊 MODULAR CAMOUFOX + BROWSER-USE VISION AGENT v2.1")
    print("="*70)
    print(f"\n📊 Configuration:")
    print(f"   Ollama: {DEFAULT_OLLAMA_BASE}")
    print(f"   Vision Model: {DEFAULT_VISION_MODEL}")
    print(f"   Text Model: {DEFAULT_TEXT_MODEL}")
    print(f"   Browser: {DEFAULT_BROWSER}")
    print(f"   Headless: {not CAMOUFOX_VISUAL}")
    print(f"\n🚀 API Server: http://0.0.0.0:5555")
    print(f"\n📚 Endpoints:")
    print(f"   GET  /health   - Health check")
    print(f"   GET  /models   - List models")
    print(f"   GET  /config   - Configuration")
    print(f"   POST /scrape   - Vision scraping (modular)")
    print(f"\n💡 Tips for n8n:")
    print(f"   - Pass model via 'model' param in JSON body")
    print(f"   - Pass custom prompt via 'system_prompt'")
    print(f"   - Pass max_steps via 'max_steps'")
    print(f"   - Add 'X-Request-ID' header for tracking")
    print(f"\n📺 VNC Display:")
    if CAMOUFOX_VISUAL:
        print(f"   ENABLED - View at http://localhost:6080")
    else:
        print(f"   DISABLED - Set CAMOUFOX_VISUAL=true to enable")
    print("\n" + "="*70 + "\n")
    
    app.run(host='0.0.0.0', port=5555, debug=False, threaded=True)
