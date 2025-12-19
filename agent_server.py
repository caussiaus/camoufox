#!/usr/bin/env python3

"""
🦊 Camoufox Vision Agent + AI Agent Control
VNC + n8n READY - Ollama browser-use agent
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

# Config – matches Coolify envs
OLLAMA_BASE = os.getenv("OLLAMABASE", "http://ollama:11434")
VISION_MODEL = os.getenv("VLMMODEL", "redule26/huihui_ai_qwen2.5-vl-7b-abliterated:latest")
AGENT_MODEL = os.getenv("AGENTMODEL", "qwen2.5:7b")

CAMOUFOX_VISUAL = os.getenv("CAMOUFOXVISUAL", "true").lower() == "true"
HEADLESS = not CAMOUFOX_VISUAL

NAV_TIMEOUT_MS = int(os.getenv("NAV_TIMEOUT_MS", "60000"))
SHOT_TIMEOUT_MS = int(os.getenv("SHOT_TIMEOUT_MS", "60000"))
DEBUG_DWELL_SEC = int(os.getenv("DEBUG_DWELL_SEC", "2"))

client = ollama.Client(host=OLLAMA_BASE)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "camoufox-vision-agent",
        "vnc_enabled": CAMOUFOX_VISUAL,
        "headless": HEADLESS,
        "vision_model": VISION_MODEL,
        "agent_model": AGENT_MODEL,
        "browser_use_available": BROWSER_USE_AVAILABLE,
        "nav_timeout_ms": NAV_TIMEOUT_MS,
        "debug_dwell_sec": DEBUG_DWELL_SEC,
        "timestamp": datetime.now().isoformat()
    })


@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.json or {}
    url = data.get("url")
    task = data.get("task", "Extract information")

    # optional agent-friendly options
    num_shots = int(data.get("num_shots", 1))
    return_images = bool(data.get("return_images", True))
    return_text = bool(data.get("return_text", True))

    if not url:
        return jsonify({"error": "Missing url"}), 400

    print(f"🦊 Scraping: {url} (shots={num_shots})")

    try:
        screenshots = []

        with Camoufox(headless=HEADLESS, humanize=True) as browser:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=NAV_TIMEOUT_MS)

            for i in range(num_shots):
                ts = int(time.time() * 1000)
                shot_path = f"/workspace/screenshots/{ts}_{i}.png"
                page.screenshot(path=shot_path, full_page=True, timeout=SHOT_TIMEOUT_MS)
                screenshots.append(shot_path)

                if CAMOUFOX_VISUAL and DEBUG_DWELL_SEC > 0:
                    time.sleep(DEBUG_DWELL_SEC)

        images_b64 = []
        for shot in screenshots:
            try:
                img = Image.open(shot).convert("RGB")
                img = img.resize((1600, 900))
                img.save(shot, format="PNG", optimize=True)

                with open(shot, "rb") as f:
                    images_b64.append(base64.b64encode(f.read()).decode())
            except Exception as e:
                print(f"⚠️ Image normalization failed for {shot}: {e}")

        analysis = None
        if return_text:
            response = client.generate(
                model=VISION_MODEL,
                prompt=f"Analyze these screenshot(s) for task: {task}",
                images=images_b64,
            )
            analysis = response["response"]

        payload = {"status": "ok"}
        if return_text:
            payload["analysis"] = analysis
        if return_images:
            payload["screenshots"] = screenshots
            payload["images_b64"] = images_b64

        return jsonify(payload)

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"status": "fail", "error": str(e)}), 500


@app.route("/agent", methods=["POST"])
def agent():
    if not BROWSER_USE_AVAILABLE:
        return jsonify({"error": "browser-use not installed (add to requirements.txt)"}), 500

    data = request.json or {}
    task = data.get("task")

    if not task:
        return jsonify({"error": "Missing task"}), 400

    model_name = data.get("model", AGENT_MODEL)

    # accept either max_actions_per_step or max_steps
    max_actions_per_step = int(
        data.get("max_actions_per_step", data.get("max_steps", 15))
    )
    headless = data.get("headless", HEADLESS)

    print(f"🦊 AI Agent: {task[:80]}... (max_actions_per_step={max_actions_per_step})")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            run_browser_agent(task, model_name, max_actions_per_step, headless)
        )
        loop.close()

        return jsonify({
            "status": "ok",
            "mode": "ai_agent",
            "task": task,
            "model": model_name,
            "result": result,
        })

    except Exception as e:
        print(f"❌ Agent error: {e}")
        return jsonify({"status": "fail", "error": str(e)}), 500


async def run_browser_agent(task: str, model_name: str,
                            max_actions_per_step: int, headless: bool):
    llm = ChatOllama(
        model=model_name,
        base_url=OLLAMA_BASE,
        temperature=0.1,
    )
    browser = Browser(
        config=BrowserConfig(
            headless=headless,
            slow_mo=200 if not headless else 0,
        )
    )
    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        max_actions_per_step=max_actions_per_step,
    )
    result = await agent.run()
    await browser.close()
    return result


if __name__ == "__main__":
    print("🦊 Camoufox Vision Agent + AI Agent STARTED")
    print(f"VNC: {'http://localhost:6080' if CAMOUFOX_VISUAL else 'DISABLED'}")
    print(f"Vision: {VISION_MODEL} | Agent: {AGENT_MODEL}")
    print(f"Browser-Use: {'✅ READY' if BROWSER_USE_AVAILABLE else '❌ MISSING'}")
    print("Endpoints: /health /scrape /agent")
    app.run(host="0.0.0.0", port=5555, debug=True)
