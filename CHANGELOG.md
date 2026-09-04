# Changelog

## 0.2.3
Built proactively from a feature request, not from a bug seen live (same
footing as 0.2.2, unlike 0.2/0.2.1). Neither piece has been through a real
session yet; treat the defaults as first guesses.

- **Session memory: summarize after a 3-hour gap instead of replaying
  everything forever.** `_handle_chat()` used to feed a customer's last 20
  raw turns into every reply, for life. Now it remembers the way a person
  remembers a regular: the *current* conversation turn by turn, older ones
  as a short written note. A customer going quiet for
  `timing.session_gap_hours` (default 3, works without the key) ends a
  session; their next message first folds every turn since the note was
  last written -- together with the previous note, so it accumulates and
  evolves instead of being overwritten -- into a fresh note via one cheap
  inline LLM call (`brain.summarize_session`, `llm.summary_model`, default
  `gpt-5.6-luna`), stored through the previously-unused
  `db.update_customer_notes()`. Notes are capped at 600 chars
  (`brain.NOTE_MAX_CHARS`). The reply call then gets only the session's
  turns plus a "lo que recuerdas de este cliente" block in the system
  prompt. No background job, cron, or thread: it is a check at the top of
  the existing per-chat path.
- `customers` gains a `notes_ts` column (guarded `ALTER TABLE` on connect,
  so an existing `ventanita.db` migrates itself). It marks both when the
  note was written and where the current session's raw replay starts. A
  failed summary call leaves it alone and replays raw history as before --
  the customer still gets their reply and the next boundary retries.
- **Typing-aware debounce: don't answer mid-sentence.** The chat-list row
  reads "typing..." while the contact is composing (observed live). After
  opening and reading a chat, `_handle_chat()` now re-OCRs that row; if it
  shows the indicator it waits (3s polls) until it clears or
  `timing.typing_wait_sec` (default 15) runs out, then re-reads the chat
  once so the reply is to the finished thought. Matches "typing" and
  "escribiendo" case-insensitively (`reader.is_typing`). Honest tradeoff:
  the wait is synchronous, so a burst of chats can each add up to the cap
  on top of their own think/typing time -- accepted over real concurrency
  for a single-window bot; keep the cap short. Costs one extra small
  row OCR per chat even when nobody is typing.
- `db.get_or_create_customer()` now returns a 5-tuple
  `(number, name, first_seen, notes, notes_ts)`; `brain.reply()` takes a
  `notes` kwarg; the HTTP call moved into one `brain._chat()` helper so
  both LLM uses share the provider/key plumbing.

## 0.2.2
Builds out the "known limitation" left open in 0.2.1. Unlike 0.2/0.2.1
these were not caught misbehaving live; they came from a research pass
over the code between test sessions. Treat them as designed-in-the-quiet
until the next live run says otherwise.

- **Drains every unread chat, not just the topmost.** `reader.find_unread_rows()`
  now returns the y of every unread badge visible in the list (pixel hits
  are clustered by `chat_list_row` height so one ~20px badge is one row,
  not twenty). `main.drain_unread()` opens the topmost allowed one, replies
  or skips, closes it, then **rescans from scratch** before touching the
  next -- opening/closing a chat and our own sent reply both reorder the
  list, so no y-coordinate is ever reused across a click.
- **Dropped the "Unread N" pill trigger (`trigger.py` deleted).** It only
  fired when the count *changed*, so one chat resolving as another arrived
  (net count unchanged, set of unread chats changed) would stall the loop.
  The row scan already answers "is anything unread right now" directly and
  is strictly at least as correct (if the pill said N>0 but no badge was on
  screen there was nothing we could open anyway), so the pill was redundant.
  `window.badge_corner` stays in config (calibrate.py still writes it) but
  nothing reads it.
- **Allowlist no longer blocks chats below a disallowed row.** Previously a
  disallowed unread chat at the top of the list made the whole cycle bail
  out, so an allowed chat under it never got checked. Now disallowed rows
  are logged and skipped and the scan keeps going down the list.
- **Per-drain cap and pause placement.** New `safety.max_chats_per_drain`
  (default 4, works without the key) bounds one pass; overflow waits for
  the next cycle. `timing.post_send_pause` now runs once after the batch
  instead of after every chat: each reply already carries its own
  `think_delay` plus real typing time, and stacking a 10-60s pause between
  four people on top of that turned a burst into a multi-minute queue.
- **Fixed every chat sharing one customer record.** `main.py` was calling
  `parser.clean(..., number="self-chat", name="self")` for every
  conversation, so all customers' orders and message history collapsed into
  one SQLite row and the LLM saw everyone's turns as one person. The OCR'd
  row label is now the identity (`parser.identity_from_label`: display name
  as `name`, slugified as the key). OCR never yields a phone number, so the
  display name is the best stable-ish key available; same-named contacts
  or a misread name will share/split a record -- documented, not solved.
- **Per-chat dedup.** Before spending an LLM call, the latest inbound line
  is compared to `db.last_user_message()` for that chat; an identical
  re-read is closed without a reply. Also skips chats where OCR read nothing.
- Drain stops opening chats once the kill switch is down (sends are refused
  after F9 until restart, so opening more would only mark them read
  unanswered).

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
