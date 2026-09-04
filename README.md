VENTANITA

Open-sourcing a billion-dollar industry with a few hundred lines of code your intern could write. Started as a 300-line napkin idea, keeps growing as real kitchens hit real edge cases — check `ventanita/` for the current count, this number goes stale fast.

---

THE PITCH DECK (THAT WILL NEVER EXIST)

"Ventanita is a next-generation, AI-native, omnichannel conversational commerce platform leveraging multimodal perception and agentic orchestration to disrupt the $4.7B customer engagement market."

Translation: it's a while-loop that reads your screen and types back.

A venture-backed startup charges you $500/month for this. They have a Series A. They have a Chief AI Officer. They have a waitlist. They have a demo video with lo-fi hip-hop and floating UI panels and a founder in a black turtleneck saying "conversational" fourteen times in ninety seconds.

We have `while True:` and a SQLite file with three columns.

Both take taco orders on a Tuesday lunch rush. One of them has a board meeting on Thursday where someone presents a slide titled "TAM Expansion Through Vertical Integration of Messaging Adjacencies." The other one has a cook who finally gets to eat lunch.

Guess which one actually solves the problem.

---

THE INDUSTRY WE'RE DESTROYING

Let's talk about the "$4.7 billion conversational AI customer engagement market."

This is an industry that looked at a cook who can't type and flip tortillas at the same time and said: "What if we built a cloud-native, SOC2-compliant, GDPR-ready, multi-tenant SaaS platform with RESTful APIs, webhook integrations, sentiment analysis dashboards, and a per-message pricing model that scales with your conversation volume?"

And then charged him $500 a month.

For a while-loop.

Let that sit.

Somewhere in a WeWork, right now, a "Head of Conversational AI" is making $180K a year to maintain a wrapper around the WhatsApp Business API that does exactly what our line 47 does. His LinkedIn says he's "passionate about leveraging LLMs to drive meaningful customer interactions at scale." His actual job is handling the case where a customer sends a voice note and the bot doesn't know what to do, so it forwards it to a human. The human is the cook. The cook is flipping tortillas. Nothing has changed except the cook now pays $500/month for the privilege of still flipping tortillas.

The entire industry is a toll booth on a road that was already free.

They didn't build a solution. They built a permission slip. You pay Meta per conversation. You pay the middleware company per message. You pay the integration partner per seat. You pay the compliance consultant per audit. You pay the support team per ticket when it breaks during your dinner rush. At no point does anyone in this chain touch a tortilla. At every point, someone invoices you.

Ventanita removes the toll booth. Not by negotiating a better rate. Not by offering a freemium tier. By walking around the building entirely and using the door that was always there — the one labeled "your own computer."

---

WHAT THIS IS

A script that watches a WhatsApp window on your monitor and replies to messages.

That's it. That's the product. There is no rest of the product.

badge goes up → click chat → read text → think → type reply → loop

You just read the entire architecture. There are no microservices hiding behind this sentence. There is no Kubernetes cluster warming up in us-east-1. There is no event-driven serverless function triggering a Lambda that writes to DynamoDB that fires a Step Function that notifies a Slack channel that pages an on-call engineer who rolls back a deployment that broke because someone updated a dependency that changed a header that Meta deprecated six months ago in a changelog nobody read.

There is a while-loop. And a cook who gets to eat lunch.

---

WHAT THIS IS NOT

Not an API integration
Not a framework
Not a platform
Not a SDK
Not a "solution"
Not clever
Not approved by Meta (they don't know it exists)
Not billable per message
Not waiting for enterprise sales to get back to you
Not going to Series B
Not hiring a VP of Growth
Not writing a blog post about "the future of conversational commerce"
Not attending SaaStr Annual

---

THE NUMBERS THAT SHOULD MAKE YOU ANGRY

Ventanita:
Setup time: an afternoon
Monthly cost: ~$0.50 in LLM tokens
Per-message fee: $0.00
Template restrictions: none
Who owns your data: you, on your disk, in a file you can open with Notepad
What happens when the vendor pivots: nothing, there is no vendor
Lines of code: a few hundred and counting, all readable in one sitting
Can you fix it at 2am during dinner rush: yes, if you can read Python

"AI Customer Engagement Platform™":
Setup time: 6-week onboarding call + 3-week integration sprint + 2-week UAT
Monthly cost: $500–$2,000
Per-message fee: $0.005–$0.08 (Meta) + whatever the middleware charges on top
Template restrictions: yes, pre-approved by Meta, 24-hour window, hope your customer doesn't reply on hour 25
Who owns your data: their cloud, their privacy policy, their subprocessors, their subprocessors' subprocessors, good luck
What happens when the vendor pivots: your bot dies, their blog post explains why "strategic realignment" means your kitchen is dark on Friday night
Lines of code: 2,000,000+ (you'll never see them, they're behind an API)
Can you fix it at 2am during dinner rush: no. You submit a ticket. You wait. Your customers wait. Your food gets cold.

The delta between these two columns is not technology. The delta is rent extraction. Every dollar in the right column that isn't in the left column is money extracted from a cook who just wanted to answer "sí, tenemos al pastor" without hiring a software company.

---

ARCHITECTURE

YOUR MONITOR

Brand A WhatsApp | Brand B WhatsApp | Brand C WhatsApp

THE SCRIPT (nine modules, one file each)

1. Badge > 0? — trigger.py
2. Click + scroll — reader.py
3. OCR last message — reader.py
4. Clean + structure — parser.py
5. Query local DB — db.py
6. Ask LLM — brain.py
7. Should we send this? — gate.py
8. Type like human — hands.py
9. Loop — main.py

Started as a napkin sketch of ~100 lines of logic. Real safety rails (kill switch, human gate, active-hours, order thresholds) add more. Still one file per job, still no framework.

SQLite (3 tables) | LLM API (rented, cents/msg) | VLM 3B (on call, photos only)

There is no diagram after this one. We considered adding more boxes to look impressive. We drew seventeen additional boxes connected by arrows labeled things like "event bus" and "message broker" and "orchestration layer." Then we deleted them all because they were lies. You're welcome.

---

THE DATABASE

CREATE TABLE customers (number TEXT, name TEXT, first_seen TEXT, notes TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer TEXT, items TEXT, status TEXT, ts TEXT);
CREATE TABLE menu (item TEXT, price REAL, available INTEGER);

Three tables. That's the schema.

A food stall needs memory, not a data warehouse. If you're reaching for Prisma, Drizzle, TypeORM, or — god forbid — a graph database to store "Juan ordered 2 al pastor," you are not solving a customer's problem. You are solving your resume's problem.

---

SCALING (OR: HOW TO GIVE A VC A HEART ATTACK)

1 brand: one window, one config file, one loop.
10 brands: ten windows, ten config files, same loop in a for-range.
N brands: N is a variable. The atom never changes.

Per-brand birth ceremony:
1. New browser profile or VM
2. Scan QR (once, forever)
3. Tile window on monitor
4. Three-line config: name, persona, menu_file

~30 minutes per brand. Brand #47 costs the same as brand #2.

We considered calling this "enterprise-grade horizontal scalability with zero marginal provisioning cost." Then we remembered we don't have a sales team, a pricing page, or a SlideShare deck with hockey stick projections. We have a for-loop. The for-loop scales. The for-loop has never once asked for equity.

---

PHILOSOPHY (OR: WHY EVERY LAYER IS FROM 2008)

BORING TECH OWNS ITS FAILURES
OCR, SQLite, mouse events — 20-year-old known failure modes. When they break, you Google the error and fix it in four minutes. Cloud APIs break on someone else's schedule, with someone else's pricing email, and someone else's idea of what "deprecated" means.

AI AS BUILDER, NOT PRODUCT
The intelligence designed this machine and sits inside it as one replaceable part in a deterministic box. Everything around the LLM is if/then. The stochastic thing touches one variable — the reply text — and nothing else. Debuggable forever. Replaceable anytime. Claude gets expensive? Point it at GPT. APIs die? Drop in a local model. The brain is rented. The body is yours.

FREEZE THE WORLD
Pinned window, fixed resolution, dark mode, zoom 100%. Perception becomes data entry, not computer vision. You don't make the model smarter. You make the world dumber. This is what roboticists have known for fifty years and what every AI startup conveniently forgets because "we handle any input" sounds better in a pitch deck than "we control the environment."

THE MONITOR IS THE DASHBOARD
Badge = queue depth. Chat list = status board. A human glance = full system observability. No Grafana. No Datadog. No PagerDuty. No $400/mo logging bill. No "observability engineer" headcount. The dashboard is the thing you were already looking at. It always was.

KISS OR GO HOME
Every coding book told you this. Chapter 3, probably. The chapter you skipped because it was too simple and you wanted to learn the framework that would get you hired. The framework got you hired. The while-loop gets the cook lunch. Different outcomes.

---

SAFETY RAILS (BECAUSE WE'RE NOT ANIMALS)

Kill switch — one key stops all typing instantly. When in doubt, kill it. The cook takes over. Tortillas survive.

Human gate — big or ambiguous orders flagged, not sent. The bot knows when it doesn't know. That makes it smarter than most VPs of Product.

Anti-ban hygiene — random delays, typing jitter, sleep hours, per-account rate caps. The bot doesn't behave like a bot. It behaves like a fast typist who takes bathroom breaks.

Fail loud — OCR confidence drops? Alert human. Never fail silent. Silent failure is how you accidentally tell a customer their order is ready when it isn't. That's not a bug. That's a lawsuit.

Sandbox — "Message yourself" chat = test environment. You talk to yourself for a week before a real customer sees anything. If you can't endure your own bot for seven days, neither can your customers.

---

INSTALL

sudo apt install tesseract-ocr tesseract-ocr-spa
git clone this repo && cd Ventanita
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp config.example.yaml config.yaml && cp .env.example .env   # then put your real key in .env
ventanita-calibrate   # once, with WhatsApp Web pinned and open
ventanita

Seven commands. One installs the OCR engine, one is a calibration wizard you run once, `pip install -e .` pulls the rest (mss, pytesseract, pyautogui, pyyaml, requests, keyboard, python-dotenv — the whole dependency list, in `pyproject.toml`). Still no onboarding call.

We considered adding a Docker Compose file, a Helm chart, a Terraform module, a GitHub Actions CI pipeline, a CONTRIBUTING.md with a PR template, a CODE_OF_CONDUCT.md, and a SECURITY.md with a responsible disclosure policy.

Then we remembered this runs on a $200 PC in a kitchen where the WiFi password is written on a napkin.

---

FAQ

Q: Does this violate WhatsApp's ToS?
A: We take screenshots of our own monitor and press keys on our own keyboard. Screen readers do this. Accessibility tools do this. RPA has done this for twenty years. We're not reverse-engineering any protocol. We're not injecting into any process. We're not scraping any server. We're using our own computer normally, just faster. Whether that violates a ToS is a question for lawyers who bill $600/hour. We bill $0/hour. We'll let you guess which answer is more useful to a cook.

Q: Won't Meta ban accounts?
A: Maybe. Random delays, human typing speed, sleep hours, and rate caps make automation indistinguishable from a fast typist. If they ban you for typing too consistently, they'll ban real humans too. Good luck explaining that to the press. "Meta bans grandmother for replying too fast to her grandson." Headline writes itself.

Q: Why not just use the official WhatsApp Business API?
A: Wonderful question. Here's the journey:

Step 1: Register a business ✓
Step 2: Verify your identity ✓
Step 3: Wait for approval ✓
Step 4: Get rejected, resubmit ✓
Step 5: Wait again ✓
Step 6: Approved! Now pay per conversation ✓
Step 7: Pre-approve message templates ✓
Step 8: Template rejected, rewrite ✓
Step 9: Resubmit template ✓
Step 10: Template approved! But only for 24-hour windows ✓
Step 11: Customer replies on hour 25, you can't respond without a new template ✓
Step 12: Submit new template ✓
Step 13: Meanwhile, your customer went to the taco stand across the street ✓
Step 14: The taco stand across the street uses Ventanita ✓
Step 15: You cry ✓

Or... scan a QR code and run a Python script. Four commands. An afternoon. Zero approvals. Zero templates. Zero per-message fees. Zero crying.

Q: Can I use this for spam?
A: Technically yes. Morally, we will find you. This is built for small food businesses taking real orders from real customers who are hungry and want al pastor. If you use it to spam, you deserve every ban, every cease-and-desist, and every karma debt the universe has in storage for you.

Q: What LLM should I use?
A: Whatever's cheapest and smart enough to understand "2 al pastor sin cebolla." Swap it anytime. The LLM is rented. The database is yours. The customer history is yours. The menu is yours. The only thing you don't own is the brain, and that's by design — brains should be commodity. If your surgeon's brain was proprietary and locked behind a subscription, you'd want a second opinion. Same logic applies here.

Q: Is this production-ready?
A: Define "production-ready."

If you mean "does it have 99.99% uptime SLA, SOC2 Type II compliance, ISO 27001 certification, a dedicated customer success manager, and a quarterly business review," then no. Absolutely not. We don't even have a logo.

If you mean "does it work on a Tuesday lunch rush, handle 500 messages an hour, not fall over when a customer sends 'hola quiero 3 de todo,' and let the cook actually cook," then yes. Emphatically yes. It does this today. In a real kitchen. With real tortillas.

Pick the definition that matters to you. If the first one matters more, you're not building a food business. You're building a compliance theater. And there are VCs who will fund that. Many of them. They'll give you millions. They'll put you on a stage. They'll call you a founder. And your cook will still be flipping tortillas alone, except now there's a Jira board tracking how lonely he is.

Q: Why open source this instead of selling it?
A: Three reasons.

One: the moment you sell it, you inherit Meta's cat-and-mouse game as permanent maintenance. They change a CSS class, ten customers go blind, and it's your phone at 7pm on a Friday. You didn't sign up for that. You signed up to cook.

Two: ban liability. When a paying customer's number gets banned, that's not a bug report. That's a livelihood. That's a phone call where someone is scared. You don't want that weight. Run it yourself and the only livelihood at risk is yours, and you can handle your own risk. You can't ethically handle someone else's.

Three: open source means the community grinds edge cases so nobody does it alone. "Bot misread sin cebolla" → someone fixes the regex → PR merged → every food stall running it gets better. Months of solo iteration become hours of collective iteration. The issues tab becomes the real product. The contributors become the R&D department that costs nothing and never quits.

Selling it = treadmill business dressed as a product business. Open sourcing it = a gift to every cook who ever lost an order because they couldn't type fast enough.

We picked the gift.

---

THE BILLION-DOLLAR INDUSTRY, EXPLAINED FOR THE LAST TIME

Here is the entire value proposition of the conversational AI customer engagement industry, stripped of every buzzword, every slide, every demo, every founder interview, every TechCrunch article, every "thought leadership" LinkedIn post:

"We will answer your customers' messages for you, using a computer, the way you would, but you have to pay us, and Meta, and the integration partner, and the compliance vendor, and also you can't customize it, and also we might break it, and also we own your data, and also good luck leaving."

That's it. That's the billion dollars.

A toll booth on a road that was already free. A permission slip for something you could already do. A middleman between a cook and a customer who both just want to say "sí, claro, en diez minutos."

Ventanita doesn't compete with this industry. Ventanita makes it irrelevant. Not by being better. Not by being cheaper. By being so simple that the emperor's new clothes become visible to everyone.

A few hundred lines of Python. A SQLite file. A pinned window. A rented brain in a small box.

The cook flips tortillas. The script answers messages. The customer gets their al pastor. Nobody pays $500 a month. Nobody submits a template for approval. Nobody waits six weeks for onboarding. Nobody presents a TAM slide.

The billion-dollar industry looks at this and says "that's not scalable."

The cook looks at this and says "that's lunch."

We know which opinion we trust.

---

THE REAL README

Everything above is marketing for people who need permission to use simple things.

Here's the truth:

A cook can't type and flip tortillas at the same time.

That's the problem. This is the solution. The rest is noise.

while True:
    if new_message():
        reply = think(read())
        type_slowly(reply)
    sleep()

Ship it.

---

Built with boring technology. Powered by spite. Funded by tacos.
No VCs were harmed in the making of this repository.
(Several pitch decks were.)

Ventanita — the little window that takes orders so you can cook.