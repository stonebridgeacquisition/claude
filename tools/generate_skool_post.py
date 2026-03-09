"""
Read .tmp/ai_news.json, call Gemini to generate a post, save to .tmp/skool_post.json
"""
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

def main():
    news_path = os.path.join(os.path.dirname(__file__), "../.tmp/ai_news.json")
    output_path = os.path.join(os.path.dirname(__file__), "../.tmp/skool_post.json")

    with open(news_path) as f:
        news = json.load(f)

    today = datetime.now().strftime("%A, %B %d, %Y")

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.0-flash")

    prompt = f"""You are writing a daily AI news digest post for a Skool community called "Zero to Auto". The audience is entrepreneurs and builders learning automation and AI.

Today is {today}.

Here is raw scraped content from 4 AI news sources:

--- HuggingFace Papers ---
{news.get('huggingface', '[unavailable]')}

--- Anthropic News ---
{news.get('anthropic', '[unavailable]')}

--- OpenAI News ---
{news.get('openai', '[unavailable]')}

--- TechCrunch AI ---
{news.get('techcrunch', '[unavailable]')}

Write a community announcement post with these rules:
- Title: Short and specific, e.g. "AI News — March 10, 2026"
- Body: 3-5 bullet points covering the most relevant, interesting developments
- Each bullet: one sentence summary + one sentence on why it matters for automation/AI builders
- Tone: Informative and direct. No hype. Minimal emojis (at most one per bullet if it genuinely helps readability, otherwise none)
- Length: 200-350 words total for the body
- End with one sentence inviting community discussion

Return valid JSON with exactly two fields: "title" and "body". No markdown, no code fences, just the raw JSON object."""

    response = model.generate_content(prompt)
    raw = response.text.strip()
    post = json.loads(raw)

    with open(output_path, "w") as f:
        json.dump(post, f, indent=2)

    print(f"[generate] Title: {post['title']}", flush=True)
    print(f"[generate] Saved to {output_path}", flush=True)

if __name__ == "__main__":
    main()
