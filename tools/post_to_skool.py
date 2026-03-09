"""
Read .tmp/skool_post.json and post it to the Skool community feed.
"""
import json
import os
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

COMMUNITY_URL = "https://www.skool.com/zero-to-auto-3053"

def main():
    post_path = os.path.join(os.path.dirname(__file__), "../.tmp/skool_post.json")
    with open(post_path) as f:
        post = json.load(f)

    title = post["title"]
    body = post["body"]

    email = os.environ["SKOOL_EMAIL"]
    password = os.environ["SKOOL_PASSWORD"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Step 1: Login
            print("[skool] Logging in...", flush=True)
            page.goto("https://www.skool.com/login", wait_until="domcontentloaded", timeout=20000)
            page.fill('input[type="email"]', email)
            page.fill('input[type="password"]', password)
            page.click('button[type="submit"]')
            # Wait until we're no longer on the login page
            page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
            print("[skool] Logged in", flush=True)

            # Step 2: Go to community
            page.goto(COMMUNITY_URL, wait_until="domcontentloaded", timeout=20000)
            print("[skool] On community page", flush=True)

            # Step 3: Open post composer by clicking "Write something"
            page.get_by_text("Write something", exact=True).click(timeout=10000)
            # Wait for the title input to confirm composer is open
            page.wait_for_selector('input[placeholder="Title"]', timeout=10000)
            print("[skool] Composer open", flush=True)

            # Step 4: Fill title
            page.get_by_placeholder("Title").fill(title)
            print("[skool] Title filled", flush=True)

            # Step 5: Type body into the contenteditable editor
            page.click('[contenteditable="true"]', timeout=10000)
            page.keyboard.type(body)
            print("[skool] Body typed", flush=True)

            # Step 6: Submit — wait for Post button to be enabled then click
            page.get_by_role("button", name="Post").click(timeout=10000)
            time.sleep(3)
            print("[skool] Post published", flush=True)

        except Exception as e:
            screenshot_path = f"/tmp/skool-debug-{int(time.time())}.png"
            page.screenshot(path=screenshot_path)
            print(f"[skool] ERROR: {e}", flush=True)
            print(f"[skool] Debug screenshot: {screenshot_path}", flush=True)
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    main()
