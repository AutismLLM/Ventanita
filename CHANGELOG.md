# Changelog

## 0.2.1
Two more real bugs found live, same session:

- **Unread-badge x-position isn't fixed.** WhatsApp shifts the badge ~22px
  left on whatever row shows the extra dropdown-chevron affordance -- which
  is exactly the freshly-bumped-to-top row that matters most. A single-pixel
  x-column scan skipped right past it and picked up a lower, unrelated
  chat's badge instead. Now scans a small x-band (`unread_badge_x_range`).
- **A customer's follow-ups went unanswered.** Confirmed live: after
  replying, the bot left the chat open. WhatsApp Web doesn't mark messages
  unread in a chat that's currently open, so the customer's next 3 messages
  never tripped the badge trigger at all. `hands.close_chat()` now returns
  to the list view after every send (skipped only on a kill-switch abort,
  so a human intervening manually keeps window focus).

Known limitation, not yet fixed: detection is still one-row-at-a-time and
assumes messages arrive with enough gap to process serially. Several chats
going unread within the same detection window is unhandled. Concept and
approach still being worked out before building it.

## 0.2
Verified end-to-end against a real, live WhatsApp Business account (isolated
virtual display, linked as an extra device -- never touches the real desktop
mouse/keyboard). Found and fixed real bugs along the way:

- **Real multi-turn memory.** New `messages` table persists per-customer chat
  turns; `brain.reply()` replays them as an actual OpenAI `messages` array
  each call. The API is still stateless per-call, but replaying full turn
  history makes it behave like one continuous session per customer.
  Verified live: correctly answered a follow-up ("Tacos que tienes?") using
  prior-turn context instead of just the latest line.
- **Fixed non-ASCII typing.** `pyautogui.write()` silently drops/mangles
  accented characters and emoji on X11. Swapped to `xdotool type`, same
  per-character jitter delay, correct UTF-8.
- **Fixed the kill switch needing root.** `keyboard.add_hotkey()` requires
  raw `/dev/input` access on Linux. Swapped to `pynput` (X11 hooks, no
  special privilege), same F9 behavior.
- **Fixed wrong-chat misfires.** `reader.py` used to click a fixed screen
  position assuming the target chat was always there. Any list reordering
  (including the bot's own sent messages bumping themselves to the top)
  could hijack that position and send a reply into the wrong chat --
  confirmed happening live. Now scans for WhatsApp's actual unread-badge
  green pixel color to find the real row before clicking.
- **Added a chat allowlist** (`safety.allowed_chats`) so the dynamic-row fix
  can't fire on arbitrary unread chats (a real contact, a community channel)
  during testing -- only configured chat name(s) get replies; everything
  else is detected but skipped and logged.
- Logs now rotate at midnight (7-day backlog) instead of growing forever,
  and print a clear bordered restart banner with PID.
- Chilango slang persona for `brain.py`'s system prompt.
- Restructured into `src/ventanita/` package layout with `pyproject.toml`
  and a real `tests/` suite (was already 0.1, carried forward).

## 0.1
- Initial v1 build: trigger/reader/parser/db/brain/gate/hands modules + main scheduler loop + calibrate.py.
- Default LLM tier set to `gpt-5.6-terra` (catches menu mismatches instead of guessing; `gpt-5.6-luna` available as a cheaper/faster swap).
- `.env` support via `python-dotenv` for API keys, kept out of git.
