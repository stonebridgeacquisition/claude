"""
Read .tmp/ai_news.json, call Claude Sonnet to generate a post, save to .tmp/skool_post.json
"""
import json
import os
from datetime import datetime
import anthropic

def main():
    news_path = os.path.join(os.path.dirname(__file__), "../.tmp/ai_news.json")
    output_path = os.path.join(os.path.dirname(__file__), "../.tmp/skool_post.json")

    with open(news_path) as f:
        news = json.load(f)

    today = datetime.now().strftime("%A, %B %d, %Y")

    # Use session OAuth token if present (Claude Code environment)
    token_file = os.environ.get("CLAUDE_SESSION_INGRESS_TOKEN_FILE", "")
    if token_file and os.path.isfile(token_file):
        with open(token_file) as tf:
            auth_token = tf.read().strip()
        client = anthropic.Anthropic(
            auth_token=auth_token,
            base_url=os.environ.get("ANTHROPIC_BASE_URL")
        )
    else:
        client = anthropic.Anthropic()

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
- Title: Short and specific, e.g. "AI News — April 19, 2026"
- Body: 3-5 bullet points covering the most relevant, interesting developments
- Each bullet: one sentence summary + one sentence on why it matters for automation/AI builders
- Tone: Informative and direct. No hype. Minimal emojis (at most one per bullet if it genuinely helps readability, otherwise none)
- Length: 200-350 words total for the body
- End with one sentence inviting community discussion

Return valid JSON with exactly two fields: "title" and "body". No markdown, no code fences, just the raw JSON object."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if present (model sometimes wraps JSON in ```json ... ```)
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rstrip("`").strip()
    post = json.loads(raw)

    with open(output_path, "w") as f:
        json.dump(post, f, indent=2)

    print(f"[generate] Title: {post['title']}", flush=True)
    print(f"[generate] Saved to {output_path}", flush=True)

if __name__ == "__main__":
    main()
