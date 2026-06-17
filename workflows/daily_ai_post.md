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

## Known Limitations (documented 2026-05-10, updated 2026-06-17)

### Chromium / Playwright not available
In containerized/cloud environments, `python3 -m playwright install chromium` fails because outbound access to Chrome for Testing CDN is blocked. Previously Chromium was pre-installed at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome` — **as of 2026-06-17 that path no longer exists**. No Chromium is available in the container. Phase 1 and Phase 3 both require Playwright; neither can run without a browser.

**Workaround for Phase 1 (news scraping):** Claude's built-in WebSearch tool can fetch current AI news even when direct HTTP is blocked. Replace the Playwright scraper with WebSearch calls from within the agent, save results directly to `.tmp/ai_news.json`. This is now the recommended approach for cloud sessions.

**Workaround for Phase 2 (generate post):** Because this workflow runs inside Claude Code, Claude itself can generate the post directly without calling `generate_skool_post.py`. The `anthropic` Python package can be installed with `pip install anthropic` if needed for standalone use.

**Phase 3 (post to Skool) remains fully blocked** — no browser is available and no Skool credentials are in the environment. See below.

### News sources blocked by network egress (HTTP 403)
All 4 sources (HuggingFace, Anthropic, OpenAI, TechCrunch) return HTTP 403 when fetched via WebFetch. Claude's WebSearch tool successfully retrieves current AI news without these restrictions and is now the fallback for Phase 1.

### .env file missing / Skool credentials not set
`SKOOL_EMAIL` and `SKOOL_PASSWORD` must be in `.env` at the repo root for Phase 3 to run. Create `.env` with:
```
SKOOL_EMAIL=your@email.com
SKOOL_PASSWORD=yourpassword
```
**Confirmed blocking in cloud sessions** — the `.env` file is gitignored and does not exist in the cloud container. Add `SKOOL_EMAIL` and `SKOOL_PASSWORD` as repository secrets or environment variables in the session settings so Phase 3 can authenticate.

### Phase 3 (post_to_skool.py) also requires Playwright
Same Chromium dependency — blocked by the same issue. Needs a browser in the environment. Until both a browser and credentials are available in the cloud session, Phase 3 cannot run automatically. The generated post is saved to `.tmp/skool_post.json` so it can be posted manually.
