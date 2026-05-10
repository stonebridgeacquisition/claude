"""
Scrape AI news from 4 sources and save to .tmp/ai_news.json.
Uses requests + BeautifulSoup (Playwright/Chromium not available in this environment).
"""
import json
import os
import re
import requests
from bs4 import BeautifulSoup

SOURCES = [
    ("huggingface", "https://huggingface.co/papers"),
    ("anthropic",   "https://www.anthropic.com/news"),
    ("openai",      "https://openai.com/news"),
    ("techcrunch",  "https://techcrunch.com/category/artificial-intelligence/"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def scrape_source(name, url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ")
        text = re.sub(r"\s+", " ", text).strip()
        print(f"[scrape] {name}: {len(text)} chars", flush=True)
        return text[:2500]
    except Exception as e:
        print(f"[scrape] {name} FAILED: {e}", flush=True)
        return f"[{name} scrape failed: {e}]"

def main():
    output_path = os.path.join(os.path.dirname(__file__), "../.tmp/ai_news.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    results = {}
    for name, url in SOURCES:
        results[name] = scrape_source(name, url)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"[scrape] Saved to {output_path}", flush=True)

if __name__ == "__main__":
    main()
