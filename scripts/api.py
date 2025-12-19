from fastapi import FastAPI, BackgroundTasks
from camoufox.sync_api import Camoufox
import os
from pathlib import Path

app = FastAPI()

SCREENSHOT_DIR = "/screenshots"
Path(SCREENSHOT_DIR).mkdir(exist_ok=True)

@app.post("/screenshot")
async def take_screenshot(url: str, filename: str = "latest.png"):
    """Take screenshot and save to shared volume"""
    with Camoufox() as browser:
        page = browser.new_page()
        page.goto(url)
        page.screenshot(path=f"{SCREENSHOT_DIR}/{filename}")
    
    return {"status": "success", "file": filename}

@app.post("/scrape")
async def scrape_page(url: str, selector: str = "body"):
    """Scrape content from page"""
    with Camoufox() as browser:
        page = browser.new_page()
        page.goto(url)
        content = page.query_selector(selector).inner_text()
    
    return {"url": url, "content": content}

@app.get("/health")
async def health():
    return {"status": "healthy"}
