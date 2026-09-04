"""brain.py — "think." The only stochastic part. Everything else is deterministic."""
import os
import requests

_SYSTEM_PROMPT = (
    "Eres el encargado del puesto, contestando por WhatsApp. Hablas en español mexicano, "
    "bien chilango, con modismos de la Ciudad de México (\"qué onda\", \"va\", \"órale\", "
    "\"al rato\", \"sale\", \"ahorita\", \"neta\", \"chido\") — natural y de volada, como si "
    "fueras cuate del cliente, no un chatbot corporativo. Nada de formalismos tipo "
    "\"Estimado cliente\". Sé breve y directo, como alguien que contesta el cel entre pedido "
    "y pedido. Usa el menú y el historial del cliente para responder. Si el pedido no queda "
    "claro, pregunta una cosa corta en vez de adivinar."
)


# Hard ceiling on a customer note. This is "what a person remembers about a
# regular", not an archive: a few sentences, not a growing essay.
NOTE_MAX_CHARS = 600

_SUMMARY_PROMPT = (
    "Eres el encargado de un puesto de tacos. Escribe en español, en tercera persona, "
    "lo que vale la pena recordar de este cliente para la próxima vez que escriba: "
    "qué suele pedir, cómo lo quiere, gustos, quejas, cosas pendientes, cómo se llama "
    "o cómo le gusta que le digan. Máximo 4 frases cortas, sin transcribir la "
    "conversación ni inventar nada. Si ya hay una nota previa, fúndela con lo nuevo "
    "en UNA sola nota corta: conserva lo que siga siendo útil, quita lo que quedó "
    "viejo. Responde solo con la nota."
)


def _build_system_content(customer_ctx, menu, recent_context="", notes=""):
    menu_lines = "\n".join(f"- {item}: ${price}" for item, price in menu)
    history_lines = "\n".join(
        f"- {items} ({status})" for items, status, _ts in customer_ctx
    )
    notes_block = (
        f"\nLo que recuerdas de este cliente de pláticas anteriores:\n{notes.strip()}\n"
        if notes and notes.strip() else ""
    )
    context_block = (
        f"\nRecent chat on screen (OCR'd — may have noise):\n{recent_context}\n"
        if recent_context else ""
    )
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"Menu:\n{menu_lines}\n\n"
        f"Customer's order history:\n{history_lines or '(none)'}\n"
        f"{notes_block}"
        f"{context_block}"
    )


def _chat(messages, llm_config, max_tokens, model=None):
    """The one HTTP call. Every LLM use in the bot goes through here so the
    provider/key plumbing lives in exactly one place. `model` overrides the
    configured one (the session summary uses a cheaper tier)."""
    llm_config = llm_config or {}
    provider = llm_config.get("provider", os.environ.get("VENTANITA_LLM_PROVIDER", "openai"))
    model = model or llm_config.get("model", os.environ.get("VENTANITA_LLM_MODEL", "gpt-5.6-terra"))
    api_key_env = llm_config.get("api_key_env", "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing LLM API key: expected env var {api_key_env}")

    if provider == "openai":
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": messages,
                "max_completion_tokens": max_tokens,
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    raise NotImplementedError(f"Unsupported LLM provider: {provider}")


def reply(message, customer_ctx, menu, llm_config=None, recent_context="", message_history=None, notes=""):
    """message_history: prior (role, content) turns for this customer, oldest first,
    NOT including the current `message` — this call appends it. Since 0.2.3 this
    is the CURRENT session only (turns since the last 3h+ gap); older sessions
    arrive as `notes`, a short summary in the system prompt, instead of raw
    replay. Replaying the session's real turns is still what makes a stateless
    API feel like one continuous conversation."""
    messages = [{
        "role": "system",
        "content": _build_system_content(customer_ctx, menu, recent_context, notes),
    }]
    for role, content in (message_history or []):
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})
    return _chat(messages, llm_config, max_tokens=200)


def summarize_session(old_notes, turns, llm_config=None):
    """Fold a finished session into the customer's note.

    old_notes (may be empty) + the (role, content) turns since it was written
    go in; one short note comes out, capped at NOTE_MAX_CHARS. Merging the old
    note into the call, instead of overwriting with only the latest session,
    is what lets the note accumulate ("always asks for extra salsa") without
    growing: the model is told to rewrite, not append.

    Uses llm.summary_model (default gpt-5.6-luna): summarizing a taco chat does
    not need the tier that answers it.
    """
    transcript = "\n".join(
        f"{'Cliente' if role == 'user' else 'Puesto'}: {content}" for role, content in turns
    )
    user_content = (
        f"Nota previa:\n{old_notes.strip() or '(ninguna)'}\n\n"
        f"Conversación desde entonces:\n{transcript or '(nada)'}"
    )
    messages = [
        {"role": "system", "content": _SUMMARY_PROMPT},
        {"role": "user", "content": user_content},
    ]
    model = (llm_config or {}).get("summary_model", "gpt-5.6-luna")
    return clip_note(_chat(messages, llm_config, max_tokens=250, model=model))


def clip_note(text, limit=NOTE_MAX_CHARS):
    """Hard cap on a note, cut at a sentence end where one is close enough so
    the prompt never ends mid-word."""
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind(".\n"))
    if end > limit // 2:
        return cut[: end + 1].strip()
    return cut.rstrip()
