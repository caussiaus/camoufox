#!/usr/bin/env python3
"""
Minimal Vision-Powered Web Agent for Docker
Uses Firefox + Abliterated Qwen2.5-VL for intelligent scraping
"""

from flask import Flask, request, jsonify
import asyncio
import time
import json
from datetime import datetime
from playwright.async_api import async_playwright
import ollama
import base64
import os

app = Flask(__name__)

# ============================================================================
# CONFIGURATION FROM ENVIRONMENT
# ============================================================================

OLLAMA_BASE = os.getenv('OLLAMA_BASE', 'http://192.168.10.50:11434')
VISION_MODEL = os.getenv('VLM_MODEL', 'qwen2-vl:7b')
TEXT_MODEL = os.getenv('TEXT_MODEL', 'qwen2.5:14b')

# Use abliterated model if available
ABLITERATED_MODEL = "redule26/huihui_ai_qwen2.5-vl-7b-abliterated:latest"

print(f"[Config] Ollama: {OLLAMA_BASE}")
print(f"[Config] Vision: {ABLITERATED_MODEL}")
print(f"[Config] Text: {TEXT_MODEL}")

# ============================================================================
# VISION SCRAPER (FIREFOX-BASED)
# ============================================================================

class VisionScraper:
    """Simple vision-powered scraper using Firefox"""
    
    def __init__(self, url: str, task: str, max_steps: int = 15):
        self.url = url
        self.task = task
        self.max_steps = max_steps
        self.start_time = time.time()
    
    async def scrape(self):
        """Extract data using vision analysis"""
        
        try:
            async with async_playwright() as p:
                # Use Firefox (installed in Docker)
                browser = await p.firefox.launch(
                    headless=True,
                    firefox_user_prefs={
                        'media.autoplay.default': 0,
                        'media.autoplay.blocking_policy': 2
                    }
                )
                
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0'
                )
                
                page = await context.new_page()
                
                try:
                    print(f"[Vision] Loading {self.url[:50]}...")
                    await page.goto(self.url, wait_until='domcontentloaded', timeout=30000)
                    await page.wait_for_timeout(2000)
                    
                    # Take screenshot
                    screenshot_bytes = await page.screenshot(full_page=False)
                    
                    # Get page text for context
                    page_text = await page.evaluate("() => document.body.innerText")
                    text_preview = page_text[:500] if page_text else "No text found"
                    
                    print(f"[Vision] Analyzing with {ABLITERATED_MODEL}...")
                    
                    # Build prompt
                    prompt = f"""Task: {self.task}

URL: {self.url}

Page text preview:
{text_preview}

Analyze this screenshot and extract relevant information for the task.
Return structured JSON with the extracted data.
Be comprehensive and accurate."""

                    # Call vision model
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                    
                    response = ollama.chat(
                        model=ABLITERATED_MODEL,
                        messages=[{
                            'role': 'user',
                            'content': prompt,
                            'images': [screenshot_b64]
                        }],
                        options={
                            'temperature': 0.2,
                            'num_ctx': 4096
                        }
                    )
                    
                    content = response['message']['content']
                    
                    # Try to parse JSON
                    try:
                        extracted_data = json.loads(content)
                    except:
                        extracted_data = {'raw_response': content}
                    
                    execution_time = time.time() - self.start_time
                    
                    print(f"[Vision] ✅ Success in {execution_time:.2f}s")
                    
                    return {
                        'status': 'ok',
                        'success': True,
                        'url': self.url,
                        'task_id': f"task_{int(time.time())}",
                        'extraction_goal': self.task,
                        'extracted_data': {
                            'primary_data': extracted_data,
                            'metadata': {
                                'source_url': self.url,
                                'extraction_method': 'vision',
                                'model': ABLITERATED_MODEL,
                                'timestamp': datetime.now().isoformat(),
                                'page_text_length': len(page_text)
                            }
                        },
                        'steps_taken': 1,
                        'action_history': ['screenshot_capture', 'vision_analysis'],
                        'screenshots': 1,
                        'execution_time': execution_time
                    }
                
                finally:
                    await page.close()
                    await context.close()
                    await browser.close()
        
        except Exception as e:
            print(f"[Vision] ❌ Error: {str(e)}")
            return {
                'status': 'fail',
                'success': False,
                'error': str(e),
                'url': self.url
            }

# ============================================================================
# FLASK API ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'camoufox-vision-agent',
        'vision_model': ABLITERATED_MODEL,
        'text_model': TEXT_MODEL,
        'browser': 'firefox',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/scrape', methods=['POST'])
def scrape():
    """
    Main scraping endpoint
    
    POST Body:
    {
        "url": "https://example.com",
        "task": "Extract product pricing",
        "user_question": "What are the prices?",
        "task_id": "optional_task_id",
        "max_steps": 15
    }
    """
    try:
        data = request.json
        
        url = data.get('url')
        task = data.get('task') or data.get('user_question', 'Extract information')
        task_id = data.get('task_id', f"task_{int(time.time())}")
        max_steps = data.get('max_steps', 15)
        
        if not url:
            return jsonify({
                'status': 'fail',
                'error': 'Missing url parameter'
            }), 400
        
        print(f"\n{'='*60}")
        print(f"[Scrape Request] {datetime.now().strftime('%H:%M:%S')}")
        print(f"URL: {url}")
        print(f"Task: {task[:60]}...")
        print(f"{'='*60}")
        
        # Run scraper
        scraper = VisionScraper(url, task, max_steps)
        result = asyncio.run(scraper.scrape())
        
        # Add task_id to result
        if result.get('success'):
            result['task_id'] = task_id
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({
            'status': 'fail',
            'success': False,
            'error': str(e)
        }), 500

@app.route('/screenshot', methods=['POST'])
def screenshot():
    """Quick screenshot endpoint"""
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'Missing url'}), 400
        
        # Quick screenshot without analysis
        async def capture():
            async with async_playwright() as p:
                browser = await p.firefox.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until='domcontentloaded')
                screenshot = await page.screenshot()
                await browser.close()
                return base64.b64encode(screenshot).decode('utf-8')
        
        screenshot_b64 = asyncio.run(capture())
        
        return jsonify({
            'status': 'ok',
            'url': url,
            'screenshot': screenshot_b64
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("  🦊 CAMOUFOX VISION AGENT - MINIMAL")
    print("="*70)
    print(f"\n🔍 Vision: {ABLITERATED_MODEL}")
    print(f"📝 Text: {TEXT_MODEL}")
    print(f"🌐 Browser: Firefox (Camoufox-ready)")
    print(f"🔗 Ollama: {OLLAMA_BASE}")
    print(f"\n🚀 Server: http://0.0.0.0:5555")
    print(f"\nEndpoints:")
    print(f"  GET  /health      - Health check")
    print(f"  POST /scrape      - Vision scraping")
    print(f"  POST /screenshot  - Quick screenshot")
    print("\n" + "="*70 + "\n")
    
    app.run(host='0.0.0.0', port=5555, debug=False, threaded=True)
