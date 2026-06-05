"""
Scrape AI news from 4 sources and save to .tmp/ai_news.json.
Uses Playwright with the pre-installed Chromium to bypass 403 blocks.
"""
import json
import os
import re
from playwright.sync_api import sync_playwright

SOURCES = [
    ("huggingface", "https://huggingface.co/papers"),
    ("anthropic",   "https://www.anthropic.com/news"),
    ("openai",      "https://openai.com/news"),
    ("techcrunch",  "https://techcrunch.com/category/artificial-intelligence/"),
]

CHROMIUM_PATH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

def scrape_source(page, name, url):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # Remove nav/footer/script noise
        page.evaluate("""
            document.querySelectorAll('script, style, nav, footer, header').forEach(e => e.remove())
        """)
        text = page.inner_text("body")
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
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=CHROMIUM_PATH,
            args=["--ignore-certificate-errors", "--no-sandbox", "--disable-setuid-sandbox"],
        )
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        for name, url in SOURCES:
            results[name] = scrape_source(page, name, url)
        browser.close()

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"[scrape] Saved to {output_path}", flush=True)

if __name__ == "__main__":
    main()
