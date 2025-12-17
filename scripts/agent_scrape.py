#!/usr/bin/env python3
"""
Intelligent Web Agent with VLM, Network Logging, and Hierarchical Planning
"""

import asyncio
from playwright.async_api import async_playwright
import base64
import json
import requests
import time
from pathlib import Path

class WebAgent:
    def __init__(self, url, task, max_steps=15):
        self.url = url
        self.task = task
        self.max_steps = max_steps
        self.step = 0
        
        # Your infrastructure
        self.ollama_base = "http://192.168.10.50:11434"
        self.vlm_model = "qwen2-vl:7b"  # Install: ollama pull qwen2-vl:7b
        self.text_model = "qwen2.5:14b"
        
        # State tracking
        self.extraction_goal = None
        self.extracted_data = []
        self.action_history = []
        self.network_logs = []
        self.console_logs = []
        self.screenshots = []
        
    async def run(self):
        """Main agent execution loop"""
        try:
            async with async_playwright() as p:
                browser = await p.firefox.launch(
                    firefox_user_prefs={
                        'privacy.resistFingerprinting': False,  # Allow normal behavior
                    }
                )
                
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0'
                )
                
                page = await context.new_page()
                
                # Setup event listeners for network/console
                self._setup_logging(page)
                
                # STRATEGIC LEVEL: Plan what to extract
                print(f"[Agent] Planning extraction strategy for: {self.task}")
                self.extraction_goal = await self.plan_extraction()
                print(f"[Agent] Goal: {json.dumps(self.extraction_goal, indent=2)}")
                
                # Navigate to page
                await page.goto(self.url, wait_until='domcontentloaded', timeout=30000)
                await self._wait_for_stability(page)
                
                # TACTICAL LEVEL: Execute actions to achieve goal
                print(f"[Agent] Starting tactical execution...")
                while self.step < self.max_steps:
                    # Capture current state
                    state = await self.capture_state(page)
                    
                    # Decide next action using VLM
                    action = await self.decide_action(state)
                    print(f"[Agent] Step {self.step}: {action['type']} - {action.get('reasoning', '')}")
                    
                    if action['type'] == 'DONE':
                        print(f"[Agent] Extraction complete after {self.step} steps")
                        break
                    
                    # Execute the action
                    result = await self.execute_action(page, action)
                    
                    self.action_history.append({
                        'step': self.step,
                        'action': action,
                        'result': result,
                        'network_events': len(self.network_logs),
                        'console_errors': len([l for l in self.console_logs if l['type'] == 'error'])
                    })
                    
                    self.step += 1
                    await asyncio.sleep(0.5)  # Brief pause between actions
                
                # Final comprehensive extraction
                final_data = await self.final_extraction(page)
                
                await browser.close()
                
                return {
                    'status': 'ok',
                    'url': self.url,
                    'task': self.task,
                    'extraction_goal': self.extraction_goal,
                    'extracted_data': final_data,
                    'steps_taken': self.step,
                    'action_history': self.action_history,
                    'network_logs': self.network_logs[-30:],  # Last 30 events
                    'console_errors': [l for l in self.console_logs if l['type'] == 'error'],
                    'screenshots': len(self.screenshots),
                    'success': True
                }
                
        except Exception as e:
            print(f"[Agent] ERROR: {str(e)}")
            return {
                'status': 'error',
                'url': self.url,
                'task': self.task,
                'error': str(e),
                'steps_taken': self.step,
                'action_history': self.action_history,
                'success': False
            }
    
    def _setup_logging(self, page):
        """Setup network and console event logging"""
        page.on('request', lambda r: self.network_logs.append({
            'type': 'request',
            'url': r.url,
            'method': r.method,
            'resource_type': r.resource_type,
            'timestamp': time.time()
        }))
        
        page.on('response', lambda r: self.network_logs.append({
            'type': 'response',
            'url': r.url,
            'status': r.status,
            'ok': r.ok,
            'timestamp': time.time()
        }))
        
        page.on('requestfailed', lambda r: self.network_logs.append({
            'type': 'failed',
            'url': r.url,
            'error': r.failure().error_text if r.failure() else 'unknown',
            'timestamp': time.time()
        }))
        
        page.on('console', lambda m: self.console_logs.append({
            'type': m.type,
            'text': m.text()[:200],  # Truncate
            'timestamp': time.time()
        }))
        
        page.on('pageerror', lambda e: self.console_logs.append({
            'type': 'page_error',
            'text': str(e)[:200],
            'timestamp': time.time()
        }))
    
    async def _wait_for_stability(self, page, timeout=5000):
        """Wait for network idle and DOM stability"""
        try:
            await page.wait_for_load_state('networkidle', timeout=timeout)
        except:
            # Continue anyway if timeout
            await asyncio.sleep(2)
    
    async def plan_extraction(self):
        """STRATEGIC LEVEL: Decide what to extract"""
        prompt = f"""You are planning a web scraping task.

Task: {self.task}

Generate an extraction plan. Return ONLY valid JSON:
{{
  "primary_goal": "main objective in one sentence",
  "data_fields": ["field1", "field2", "field3"],
  "success_criteria": "how to know extraction is complete",
  "expected_obstacles": ["cookie banner", "paywall", "dynamic loading"],
  "priority_actions": ["dismiss popups first", "navigate to data section"]
}}

Be specific about what data to extract."""

        try:
            response = requests.post(f'{self.ollama_base}/api/generate', json={
                'model': self.text_model,
                'prompt': prompt,
                'stream': False,
                'format': 'json',
                'options': {'temperature': 0.3}
            }, timeout=30)
            
            return json.loads(response.json()['response'])
        except Exception as e:
            print(f"[Agent] Planning error: {e}, using default")
            return {
                "primary_goal": self.task,
                "data_fields": ["main content"],
                "success_criteria": "data extracted",
                "expected_obstacles": ["cookie banner"],
                "priority_actions": ["dismiss popups", "extract data"]
            }
    
    async def capture_state(self, page):
        """Capture current page state for VLM analysis"""
        # Screenshot (most important for VLM)
        screenshot = await page.screenshot(full_page=False)  # Viewport only
        screenshot_b64 = base64.b64encode(screenshot).decode()
        self.screenshots.append(screenshot_b64)
        
        # Get clickable elements
        elements = await page.evaluate("""
            () => {
                const clickable = document.querySelectorAll(
                    'button, a, input[type="submit"], input[type="button"], ' +
                    '[role="button"], .cookie, .modal, .popup, .close, .accept'
                );
                return Array.from(clickable).slice(0, 50).map((el, idx) => {
                    const rect = el.getBoundingClientRect();
                    return {
                        index: idx,
                        tag: el.tagName,
                        text: (el.innerText || el.value || el.getAttribute('aria-label') || '').slice(0, 50),
                        type: el.type || '',
                        id: el.id || '',
                        class: el.className || '',
                        visible: el.offsetParent !== null && rect.width > 0 && rect.height > 0,
                        x: Math.round(rect.x),
                        y: Math.round(rect.y)
                    };
                }).filter(el => el.visible);
            }
        """)
        
        # Visible text content
        visible_text = await page.evaluate("""
            () => {
                return document.body.innerText.slice(0, 3000);
            }
        """)
        
        # Page metadata
        title = await page.title()
        url = page.url
        
        return {
            'screenshot': screenshot_b64,
            'elements': elements,
            'text': visible_text,
            'url': url,
            'title': title,
            'step': self.step
        }
    
    async def decide_action(self, state):
        """TACTICAL LEVEL: Decide next action based on current state"""
        # Recent network activity (for context)
        recent_network = [
            log for log in self.network_logs[-15:]
            if time.time() - log['timestamp'] < 10
        ]
        
        # Check for ongoing network activity
        loading = len([n for n in recent_network if n['type'] == 'request']) > 0
        
        # Recent errors
        recent_errors = [
            log for log in self.console_logs[-10:]
            if log['type'] in ['error', 'page_error'] and time.time() - log['timestamp'] < 10
        ]
        
        prompt = f"""You are a web automation agent on step {self.step}/{self.max_steps}.

EXTRACTION GOAL:
{json.dumps(self.extraction_goal, indent=2)}

CURRENT STATE:
- URL: {state['url']}
- Title: {state['title']}
- Visible elements: {len(state['elements'])} clickable items
- Network loading: {'YES - wait' if loading else 'NO - ready'}
- Console errors: {len(recent_errors)}

ACTION HISTORY (last 3):
{json.dumps(self.action_history[-3:], indent=2) if self.action_history else 'None'}

AVAILABLE ELEMENTS TO CLICK:
{json.dumps(state['elements'][:15], indent=2)}

TEXT PREVIEW:
{state['text'][:500]}

NETWORK ACTIVITY (last 10s):
{json.dumps(recent_network[-5:], indent=2)}

DECISION RULES:
1. If cookie banner/popup visible → CLICK to dismiss
2. If loading → WAIT
3. If extraction goal data is visible → EXTRACT
4. If stuck (same action 3+ times) → DONE
5. If target data found → DONE
6. If need more content → SCROLL

Return ONLY valid JSON:
{{
  "type": "CLICK|SCROLL|EXTRACT|WAIT|DONE",
  "reasoning": "brief explanation",
  "element_index": 5,
  "scroll_direction": "down",
  "confidence": 0.9
}}"""

        try:
            response = requests.post(f'{self.ollama_base}/api/generate', json={
                'model': self.vlm_model,
                'prompt': prompt,
                'images': [state['screenshot']],
                'stream': False,
                'format': 'json',
                'options': {'temperature': 0.2}
            }, timeout=45)
            
            decision = json.loads(response.json()['response'])
            
            # Validation
            if 'type' not in decision:
                decision = {'type': 'EXTRACT', 'reasoning': 'fallback', 'confidence': 0.5}
            
            return decision
            
        except Exception as e:
            print(f"[Agent] Decision error: {e}, defaulting to EXTRACT")
            return {
                'type': 'EXTRACT',
                'reasoning': f'Error in decision: {str(e)}',
                'confidence': 0.3
            }
    
    async def execute_action(self, page, action):
        """Execute the decided action"""
        try:
            action_type = action['type']
            
            if action_type == 'CLICK':
                idx = action.get('element_index', 0)
                await page.evaluate(f"""
                    (() => {{
                        const clickable = document.querySelectorAll(
                            'button, a, input[type="submit"], input[type="button"], ' +
                            '[role="button"], .cookie, .modal, .popup, .close, .accept'
                        );
                        const el = Array.from(clickable).filter(e => e.offsetParent !== null)[{idx}];
                        if (el) {{
                            el.click();
                            return true;
                        }}
                        return false;
                    }})()
                """)
                await asyncio.sleep(1)
                await self._wait_for_stability(page, timeout=3000)
                return {'status': 'clicked', 'element': idx}
            
            elif action_type == 'SCROLL':
                direction = action.get('scroll_direction', 'down')
                distance = 800 if direction == 'down' else -800
                await page.evaluate(f"window.scrollBy(0, {distance})")
                await asyncio.sleep(0.5)
                return {'status': 'scrolled', 'direction': direction}
            
            elif action_type == 'EXTRACT':
                data = await page.evaluate("""
                    () => {
                        return {
                            headers: Array.from(document.querySelectorAll('h1,h2,h3'))
                                .map(h => h.innerText.trim()).filter(t => t),
                            paragraphs: Array.from(document.querySelectorAll('p'))
                                .map(p => p.innerText.trim()).filter(t => t && t.length > 20),
                            lists: Array.from(document.querySelectorAll('ul li, ol li'))
                                .map(li => li.innerText.trim()).filter(t => t),
                            tables: Array.from(document.querySelectorAll('table'))
                                .map(t => t.innerText.trim()).slice(0, 3),
                            links: Array.from(document.querySelectorAll('a'))
                                .map(a => ({text: a.innerText.trim(), href: a.href}))
                                .filter(l => l.text).slice(0, 20)
                        };
                    }
                """)
                self.extracted_data.append(data)
                return {'status': 'extracted', 'items': len(str(data))}
            
            elif action_type == 'WAIT':
                await asyncio.sleep(2)
                await self._wait_for_stability(page)
                return {'status': 'waited', 'duration': 2}
            
            elif action_type == 'DONE':
                return {'status': 'completed'}
            
            else:
                return {'status': 'unknown_action', 'action': action_type}
                
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    async def final_extraction(self, page):
        """Final comprehensive extraction using VLM"""
        state = await self.capture_state(page)
        
        prompt = f"""FINAL DATA EXTRACTION

Original Task: {self.task}

Extraction Goal:
{json.dumps(self.extraction_goal, indent=2)}

Current Page:
- Title: {state['title']}
- URL: {state['url']}

Data Extracted During Navigation:
{json.dumps(self.extracted_data, indent=2)}

Page Text:
{state['text']}

TASK: Extract ALL relevant data that matches the extraction goal. Structure it according to the data_fields specified in the goal.

Return ONLY valid JSON matching this structure:
{{
  "primary_data": {{}},
  "metadata": {{
    "source_url": "{state['url']}",
    "extraction_date": "{time.strftime('%Y-%m-%d')}"
  }},
  "confidence": 0.9
}}"""

        try:
            response = requests.post(f'{self.ollama_base}/api/generate', json={
                'model': self.vlm_model,
                'prompt': prompt,
                'images': [state['screenshot']],
                'stream': False,
                'format': 'json',
                'options': {'temperature': 0.1}
            }, timeout=60)
            
            final = json.loads(response.json()['response'])
            return final
            
        except Exception as e:
            print(f"[Agent] Final extraction error: {e}")
            # Fallback: return what we collected
            return {
                'primary_data': self.extracted_data,
                'metadata': {
                    'source_url': state['url'],
                    'extraction_date': time.strftime('%Y-%m-%d'),
                    'extraction_method': 'fallback'
                },
                'confidence': 0.5,
                'error': str(e)
            }


async def main():
    """CLI entry point"""
    import sys
    if len(sys.argv) < 3:
        print("Usage: python agent_scrape.py <url> <task> [max_steps]")
        sys.exit(1)
    
    url = sys.argv[1]
    task = sys.argv[2]
    max_steps = int(sys.argv[3]) if len(sys.argv) > 3 else 15
    
    agent = WebAgent(url, task, max_steps)
    result = await agent.run()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
