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


def reply(message, customer_ctx, menu, llm_config=None):
    llm_config = llm_config or {}
    provider = llm_config.get("provider", os.environ.get("VENTANITA_LLM_PROVIDER", "openai"))
    model = llm_config.get("model", os.environ.get("VENTANITA_LLM_MODEL", "gpt-5.6-terra"))
    api_key_env = llm_config.get("api_key_env", "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing LLM API key: expected env var {api_key_env}")

    prompt = _build_prompt(message, customer_ctx, menu)

    if provider == "openai":
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_completion_tokens": 200,
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    raise NotImplementedError(f"Unsupported LLM provider: {provider}")
