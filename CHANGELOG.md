# Changelog

## 0.1
- Initial v1 build: trigger/reader/parser/db/brain/gate/hands modules + main scheduler loop + calibrate.py.
- Default LLM tier set to `gpt-5.6-terra` (catches menu mismatches instead of guessing; `gpt-5.6-luna` available as a cheaper/faster swap).
- `.env` support via `python-dotenv` for API keys, kept out of git.
