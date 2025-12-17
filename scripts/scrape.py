#!/usr/bin/env python3
"""Camoufox scraper with intelligent context-aware extraction"""
import json
import sys
import os
from pathlib import Path

try:
    from camoufox.sync_api import Camoufox
except ImportError:
    print(json.dumps({
        'error': 'Camoufox not available',
        'status': 'fail'
    }))
    sys.exit(1)

def scrape_url(url, task_id, user_question=None, headless=True):
    """
    Scrape a URL with context awareness
    
    Args:
        url: Target URL
        task_id: Unique task identifier
        user_question: Original user question for context
        headless: Run headless or visual
    """
    ss_dir = Path('/workspace/screenshots')
    ss_dir.mkdir(exist_ok=True)

    try:
        # Check if we should run in visual mode
        visual_mode = os.environ.get('CAMOUFOX_VISUAL', 'true').lower() == 'true'
        use_headless = headless and not visual_mode

        with Camoufox(headless=use_headless, humanize=True) as browser:
            page = browser.new_page()
            page.goto(url, timeout=20000)
            page.wait_for_timeout(3000)

            # Screenshot
            ss_path = ss_dir / f'{task_id}.png'
            page.screenshot(path=str(ss_path))

            # INTELLIGENT EXTRACTION (not hardcoded!)
            # Get structured elements for LLM to judge
            elements = []
            
            # Headers (indicate structure/topics)
            for tag in ['h1', 'h2', 'h3']:
                try:
                    for el in page.query_selector_all(f'{tag}')[:5]:
                        text = el.inner_text().strip()
                        if len(text) > 3:
                            elements.append({
                                'type': tag,
                                'text': text
                            })
                except Exception:
                    pass
            
            # Paragraphs (content)
            try:
                for el in page.query_selector_all('p')[:15]:
                    text = el.inner_text().strip()
                    if len(text) > 50:  # Meaningful paragraphs only
                        elements.append({
                            'type': 'paragraph',
                            'text': text[:500]  # Limit length
                        })
            except Exception:
                pass
            
            # Lists (often contain key info)
            try:
                for el in page.query_selector_all('li')[:10]:
                    text = el.inner_text().strip()
                    if len(text) > 20:
                        elements.append({
                            'type': 'list_item',
                            'text': text[:300]
                        })
            except Exception:
                pass
            
            # Prices (if looking for products)
            price_selectors = [
                '[class*="price"]',
                '[class*="cost"]',
                '[data-price]'
            ]
            
            for selector in price_selectors:
                try:
                    for el in page.query_selector_all(selector)[:5]:
                        text = el.inner_text().strip()
                        if text:
                            elements.append({
                                'type': 'price',
                                'text': text
                            })
                except Exception:
                    pass
            
            # Get full page text as fallback
            try:
                full_text = page.inner_text('body')
            except Exception:
                full_text = ""

            result = {
                'url': url,
                'task_id': task_id,
                'title': page.title(),
                'screenshot': str(ss_path),
                'screenshot_url': f'/camoufox-screenshots/{task_id}.png',
                'elements': elements,  # Structured data for LLM
                'full_text': full_text[:3000],  # First 3000 chars
                'user_question': user_question,  # CONTEXT!
                'status': 'ok'
            }

            page.close()
            print(json.dumps(result))

    except Exception as e:
        print(json.dumps({
            'url': url,
            'task_id': task_id,
            'error': str(e),
            'status': 'fail'
        }))

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(json.dumps({
            'error': 'Usage: scrape.py <url> <task_id> [user_question] [headless]',
            'status': 'fail'
        }))
        sys.exit(1)

    url = sys.argv[1]
    task_id = sys.argv[2]
    user_question = sys.argv[3] if len(sys.argv) > 3 else None
    headless = sys.argv[4].lower() != 'false' if len(sys.argv) > 4 else True

    scrape_url(url, task_id, user_question, headless)
