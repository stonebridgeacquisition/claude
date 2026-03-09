"""
Scrape AI news from 4 sources and save to .tmp/ai_news.json
"""
import json
import os
import sys
from playwright.sync_api import sync_playwright

SOURCES = [
    ("huggingface", "https://huggingface.co/papers"),
    ("anthropic",   "https://www.anthropic.com/news"),
    ("openai",      "https://openai.com/news"),
    ("techcrunch",  "https://techcrunch.com/category/artificial-intelligence/"),
]

def scrape_source(page, name, url):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        text = page.inner_text("body")
        print(f"[scrape] {name}: {len(text)} chars", flush=True)
        return text[:2500]
    except Exception as e:
        print(f"[scrape] {name} FAILED: {e}", flush=True)
        return f"[{name} scrape failed: {e}]"

def main():
    output_path = os.path.join(os.path.dirname(__file__), "../.tmp/ai_news.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Open all pages in parallel using separate pages on one browser
        pages = [browser.new_page() for _ in SOURCES]
        for (name, url), pg in zip(SOURCES, pages):
            results[name] = scrape_source(pg, name, url)
            pg.close()
        browser.close()

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"[scrape] Saved to {output_path}", flush=True)

if __name__ == "__main__":
    main()
