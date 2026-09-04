"""brain.py — "think." The only stochastic part. Everything else is deterministic."""
import os
import requests

_SYSTEM_PROMPT = (
    "You are the counter person for a small food stand, replying over WhatsApp. "
    "Be warm, brief, and direct, like a real person texting between orders. "
    "Use the menu and the customer's order history to answer. "
    "If the order is unclear, ask one short clarifying question instead of guessing."
)


def _build_prompt(message, customer_ctx, menu):
    menu_lines = "\n".join(f"- {item}: ${price}" for item, price in menu)
    history_lines = "\n".join(
        f"- {items} ({status})" for items, status, _ts in customer_ctx
    )
    return (
        f"Menu:\n{menu_lines}\n\n"
        f"Customer's recent orders:\n{history_lines or '(none)'}\n\n"
        f"Customer says: {message}"
    )


def reply(message, customer_ctx, menu):
    provider = os.environ.get("VENTANITA_LLM_PROVIDER", "openai")
    api_key = os.environ.get("OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Missing LLM API key in environment")

    prompt = _build_prompt(message, customer_ctx, menu)

    if provider == "openai":
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": os.environ.get("VENTANITA_LLM_MODEL", "gpt-4o-mini"),
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 200,
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    raise NotImplementedError(f"Unsupported LLM provider: {provider}")
