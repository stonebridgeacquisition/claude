"""
Send a Telegram message to notify that the daily Skool post was published.
Reads .tmp/skool_post.json for the post content.
"""
import json
import os
import urllib.request
import urllib.parse
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

def send_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

def main():
    post_path = os.path.join(os.path.dirname(__file__), "../.tmp/skool_post.json")
    with open(post_path) as f:
        post = json.load(f)

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    message = (
        f"✅ *Daily Skool post published*\n\n"
        f"*{post['title']}*\n\n"
        f"{post['body']}"
    )

    # Telegram max message length is 4096 chars
    if len(message) > 4096:
        message = message[:4093] + "..."

    send_message(token, chat_id, message)
    print("[telegram] Notification sent", flush=True)

if __name__ == "__main__":
    main()
