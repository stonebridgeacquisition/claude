# Workflow: Daily AI Post to Skool

## Objective
Each day at 6 PM, research the latest AI developments and post a clean digest to the Zero to Auto Skool community Announcements section.

## Inputs
- `.env`: `ANTHROPIC_API_KEY`, `SKOOL_EMAIL`, `SKOOL_PASSWORD`
- Community URL: `https://www.skool.com/zero-to-auto-3053`

## Steps

### Phase 1 — Scrape AI news
**Tool:** `tools/scrape_ai_news.py`
**Output:** `.tmp/ai_news.json`

Scrapes 4 sources in parallel using Playwright (headless Chromium):
- HuggingFace Papers: `https://huggingface.co/papers`
- Anthropic News: `https://www.anthropic.com/news`
- OpenAI News: `https://openai.com/news`
- TechCrunch AI: `https://techcrunch.com/category/artificial-intelligence/`

Each source gets up to 2500 chars of body text. If a source fails, the error string is saved and passed forward — Claude will note the gap in the post.

### Phase 2 — Generate post
**Tool:** `tools/generate_skool_post.py`
**Input:** `.tmp/ai_news.json`
**Output:** `.tmp/skool_post.json`

Calls Claude Sonnet with all scraped content and instructions to produce a JSON post: `{ "title": "...", "body": "..." }`. Format: 3-5 bullet points, informative/clean, 200-350 words, minimal emojis, ends with a discussion invite.

### Phase 3 — Post to Skool
**Tool:** `tools/post_to_skool.py`
**Input:** `.tmp/skool_post.json`

Uses Playwright to:
1. Log in at `skool.com/login`
2. Navigate to community
3. Click Announcements tab
4. Open post composer
5. Fill title + type body into contenteditable editor
6. Submit

On failure: saves a debug screenshot to `/tmp/skool-debug-*.png`.

## Running

**Manual test (visible browser):**
```bash
python3 tools/run_daily_ai_post.py
```
`headless=False` is the default in `post_to_skool.py` — watch the browser to verify selectors.

**Switch to headless after confirmed working:**
In `tools/post_to_skool.py`, change `headless=False` → `headless=True`

**Cron (6 PM daily):**
```
0 18 * * * cd /Users/salim/claude && /Users/salim/Library/Python/3.9/bin/python3 tools/run_daily_ai_post.py >> /Users/salim/claude/.tmp/daily_post.log 2>&1
```

## Edge Cases
- If a news source is down: the tool passes the error string to Claude; Claude generates from remaining sources
- If Skool selector breaks: debug screenshot saved to `/tmp/skool-debug-*.png`; update the selector in `post_to_skool.py` and re-run
- If Claude returns malformed JSON: `generate_skool_post.py` will throw a parse error — check `.tmp/ai_news.json` and re-run phase 2 manually

## Self-Improvement
When selectors change or sources go down, update this workflow and the relevant tool. Document the fix here.

## Known Limitations (documented 2026-05-10)

### Chromium / Playwright not available
In containerized/cloud environments, `python3 -m playwright install chromium` fails because outbound access to Chrome for Testing CDN is blocked. Fallback: `scrape_ai_news.py` was rewritten to use `requests` + `BeautifulSoup`.

### All 4 news sources return 403 with requests
HuggingFace, Anthropic, OpenAI, and TechCrunch all block plain `requests` with a proper `User-Agent`. The original Playwright approach was specifically needed to bypass this. Until a browser is available, the scraper will always pass error strings to Claude. Claude will generate a honest "sources unavailable" post (see `.tmp/skool_post.json` for example output).

**Fix options:**
- Install a full browser (Chromium/Firefox) in the environment so Playwright can use it with `executable_path`
- Use a paid scraping proxy service (e.g. ScrapingBee, Browserless) — add API key to `.env` and update `scrape_ai_news.py`

### .env file missing
`SKOOL_EMAIL` and `SKOOL_PASSWORD` must be in `.env` at the repo root for Phase 3 to run. Create `.env` with:
```
SKOOL_EMAIL=your@email.com
SKOOL_PASSWORD=yourpassword
```

### Phase 3 (post_to_skool.py) also requires Playwright
Same Chromium dependency — blocked by the same issue. Needs a browser in the environment.
