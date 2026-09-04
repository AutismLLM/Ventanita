# VENTANITA — Tech Outline (Build Spec for Fable/Claude)

*Hand this to the builder. Everything needed to ship v1. No philosophy, no pitch — just the blueprint.*

---

## 0. Scope & Non-Goals

**In scope (v1):** Single-brand, single-window, self-chat sandbox → one live brand. OCR trigger, local DB, rented LLM reply, human-like typing, kill switch.

**Out of scope (v1):** Multi-brand fleet, VM orchestration, payment processing, voice notes, image replies, web dashboard. *These are v2. Do not build them yet. The atom first.*

**Golden rule:** If a feature adds a dependency or a framework, it doesn't ship in v1. Boring tech only.

---

## 1. Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Readable at 2am, universal |
| Screen input | `mss` (fast screenshot) + region crop | Faster than pyautogui.screenshot |
| OCR | `pytesseract` (Tesseract) | Free, solved problem, dark-mode friendly |
| Optional VLM | local 3B (LLaVA / Qwen-VL) via `llama.cpp` | On-call only, photos/ambiguity |
| Mouse/keyboard | `pyautogui` | Click + type with jitter |
| DB | `sqlite3` (stdlib) | One file, zero server |
| LLM | HTTP call to any chat API (OpenAI/Anthropic/local) | Swappable, behind one function |
| Config | `config.yaml` | Window coords, LLM key, paths, timings |
| Logging | `logging` to `ventanita.log` | Fail loud, reviewable |

**Total external deps:** `mss`, `pytesseract`, `pyautogui`, `pyyaml`, `requests`. Five. That's the ceiling.

---

## 2. System Layout

```
[Monitor: WhatsApp window, FIXED position/size, dark mode, zoom 100%]
        │
        ▼  (mss region capture)
┌──────────────────────────────────────┐
│           ventanita.py               │
│                                      │
│  scheduler loop (every N sec)        │
│   ├─ trigger.badge_changed()?        │
│   ├─ reader.last_messages()          │
│   ├─ parser.clean(text)              │
│   ├─ db.get_customer(number)         │
│   ├─ brain.reply(msg, context)       │
│   ├─ gate.should_send(reply)?        │
│   └─ hands.type_and_send(reply)      │
└──────────────────────────────────────┘
        │            │            │
     sqlite.db   LLM API    config.yaml
```

---

## 3. Module Breakdown (one file each, ~300 lines total)

### `config.yaml`
```yaml
window:
  region: [x, y, w, h]        # chat area rectangle
  badge_corner: [x, y, w, h]  # tiny unread-badge crop
  input_pos: [x, y]           # click point for input field
  chat_list_row: [x, y, w, h] # row to click when badge appears
timing:
  check_interval_sec: 5
  think_delay: [3, 15]        # random range before reply
  type_jitter: [0.03, 0.12]   # per-char delay
  post_send_pause: [10, 60]
  active_hours: [8, 22]       # sleep outside this
llm:
  provider: openai            # or anthropic / local
  model: gpt-4o-mini
  api_key_env: OPENAI_API_KEY
paths:
  db: ./ventanita.db
  menu: ./menu.txt
  log: ./ventanita.log
safety:
  max_reply_chars: 320
  confirm_above_mxn: 500      # human gate threshold
  killswitch_key: f9
```

### `trigger.py` — "did anything happen?" (~15 lines)
- Crop `badge_corner`, color-threshold for green blob → bool
- OCR that 20×20px crop → digit (or 0)
- Compare to last value → `changed: bool`
- **No VLM here. Dumb, fast, free.**

### `reader.py` — "what does it say?" (~20 lines)
- Click `chat_list_row` (the chat with the badge)
- Scroll to bottom
- Capture `window.region`, OCR → raw text
- Return raw string

### `parser.py` — "make it clean" (~30 lines)
- Strip timestamps, system messages, own replies
- Extract: sender hint, latest inbound line
- Structure food intent: regex/lightweight → `{item, qty, note}` (e.g. "2 al pastor sin cebolla")
- This is the error-shrinking layer. LLM only sees cleaned output.

### `db.py` — "memory" (~40 lines)
```sql
customers(number TEXT PRIMARY KEY, name TEXT, first_seen TEXT, notes TEXT)
orders(id INTEGER PK, customer TEXT, items TEXT, status TEXT, ts TEXT)
menu(item TEXT, price REAL, available INTEGER)
```
- `get_or_create_customer(number, name)`
- `recent_orders(number, n=3)`
- `active_menu()` → list of available items
- `add_order(...)`, `update_status(...)`

### `brain.py` — "think" (~30 lines)
- One function: `reply(message, customer_ctx, menu) -> str`
- Builds prompt: system (persona from config) + menu + customer history + the message
- Calls LLM behind a single swappable HTTP function
- **LLM is the ONLY stochastic part.** Everything else deterministic.
- Optional: if `parser` confidence low OR message has image → call local VLM first, feed its description into the prompt.

### `gate.py` — "should we really send this?" (~20 lines)
- Reply too long? → truncate/flag
- Order total > `confirm_above_mxn`? → flag human, don't send
- Ambiguous parse? → flag
- Outside `active_hours`? → queue, don't send
- Returns `(send: bool, reason: str)`

### `hands.py` — "type like a human" (~30 lines)
- Click `input_pos`
- Type char-by-char with `type_jitter` random delay
- Random pre-type pause (`think_delay`)
- Press enter
- **Kill switch listener:** global hotkey (`f9`) sets a flag → abort typing mid-message immediately.

### `scheduler.py` / `main.py` — "the loop" (~20 lines)
```python
while running:
    if not in_active_hours(): sleep(60); continue
    if trigger.badge_changed():
        raw = reader.last_messages()
        msg = parser.clean(raw)
        cust = db.get_or_create_customer(msg.number, msg.name)
        ctx = db.recent_orders(msg.number) + db.active_menu()
        reply = brain.reply(msg.text, ctx)
        ok, reason = gate.should_send(reply, msg)
        if ok: hands.type_and_send(reply)
        else: log.flag(reason, msg, reply)
    sleep(check_interval)
```

---

## 4. The Frozen World (setup, once)

1. Pin WhatsApp window, fixed size, dark mode, zoom 100%, notifications OFF
2. Run a `calibrate.py` helper: click corners → writes `window.region`, `badge_corner`, `input_pos` into config
3. Never move the window. If it moves, recalibrate. (v2: VLM removes this need.)

---

## 5. Safety & Anti-Ban

- Kill switch (global hotkey) — instant stop
- Human gate on high-value/ambiguous
- Random delays everywhere (ranges in config)
- Active-hours sleep
- Per-account rate cap (max N sends/hour)
- Fail loud: OCR confidence < threshold → log + alert, never silent
- Sandbox first: point config at "Message yourself" chat for a full week before any real customer

---

## 6. Build Order (do it in this sequence)

1. `trigger` + `reader` on self-chat → prove you can detect and read
2. `parser` + `db` → prove you can clean and remember
3. `brain` → prove the LLM answers sensibly with menu context
4. `hands` + kill switch → prove you can type safely
5. `gate` → prove it stops itself when unsure
6. `scheduler` wires it together → run on self-chat 7 days
7. One live brand, supervised → then consider v2 (fleet)

---

## 7. v2 Hooks (do NOT build now, just leave the seams)

- `brand_id` column ready in DB schema
- `brain.persona` already comes from config → per-brand = per-config
- `reader`/`trigger` take a `region` arg → multi-window = loop over regions
- LLM behind one function → swap provider without touching anything else

---

That's the whole spec. ~300 lines, five deps, one SQLite file, one pinned window. Hand it to Fable Claude and tell it: **build the atom, nothing more, boring tech only, kill switch non-negotiable.** 🪽