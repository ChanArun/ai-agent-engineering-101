from __future__ import annotations

import json
import os
import re
from typing import Any

from openai import OpenAI


MODEL = os.getenv(
    "AGENT_MODEL",
    "openai/gpt-oss-120b",
)

BASE_URL = os.getenv(
    "OPENAI_BASE_URL",
    "https://api.groq.com/openai/v1",
)

API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is not set."
    )


client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)


def _extract_json(text: str) -> dict[str, Any]:
    """
    Parse a JSON object from the model response.

    The model is instructed to return JSON only,
    but this also tolerates fenced JSON or a small
    amount of surrounding text.
    """
    text = text.strip()

    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    fenced = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if fenced:
        value = json.loads(fenced.group(1))
        if isinstance(value, dict):
            return value

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end > start:
        value = json.loads(
            text[start : end + 1]
        )

        if isinstance(value, dict):
            return value

    raise ValueError(
        f"Model did not return a JSON object: {text!r}"
    )


def _call_json(
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any]:
    """
    Call the GroqCloud model and require a JSON
    decision. Retry once if the first response is
    not valid JSON.
    """

    last_error: Exception | None = None

    for attempt in range(2):
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]

        if attempt == 1:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your previous answer was not "
                        "valid JSON. Return ONLY the "
                        "requested JSON object."
                    ),
                }
            )

        response = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            reasoning_effort="low",
            messages=messages,
        )

        text = (
            response.choices[0]
            .message.content
            or ""
        )

        try:
            return _extract_json(text)
        except Exception as exc:
            last_error = exc

    raise RuntimeError(
        f"Harness failed to return valid JSON: "
        f"{last_error}"
    )


def seller_opening(
    *,
    item: str,
    reserve: int,
) -> dict[str, Any]:
    """
    Let the model choose the seller's opening price.
    """

    system = """
You are the decision-making harness for an A2A seller.

You negotiate commercially but safely.

Rules:
- You sell the named item.
- The reserve is the absolute minimum legal selling price.
- Never ask below the reserve.
- Choose a realistic opening price that leaves room to negotiate.
- The negotiation should still have a reasonable chance to succeed.
- You must make the pricing decision yourself.

Return ONLY JSON:
{"action":"ask","price":INTEGER}
""".strip()

    user = f"""
Item: {item}
Seller reserve: {reserve}

Choose the opening asking price.
""".strip()

    result = _call_json(
        system,
        user,
    )

    if result.get("action") != "ask":
        raise ValueError(
            f"Unexpected seller opening action: {result}"
        )

    price = int(result["price"])

    # Safety enforcement in code as well as prompt.
    if price < reserve:
        price = reserve

    return {
        "action": "ask",
        "price": price,
    }


def seller_turn(
    *,
    item: str,
    reserve: int,
    current_ask: int,
    buyer_offer: int,
    turn_number: int,
    history: list[str],
) -> dict[str, Any]:
    """
    Let the model decide whether to accept,
    counteroffer, or reject.
    """

    system = """
You are the decision-making harness for an A2A seller.

You must decide every negotiation action.

Rules:
- The reserve is the absolute minimum legal selling price.
- Never accept a buyer offer below the reserve.
- Never counteroffer below the reserve.
- If the buyer offers at least the reserve, accepting is normally the best choice.
- If the offer is below reserve, negotiate with a counteroffer at or above reserve.
- Do not reject too early when the buyer is still making progress.
- Reject only when continuing negotiation is no longer useful.
- Keep the negotiation short and practical.

Return ONLY one of these JSON objects:

{"action":"accept"}
{"action":"counter","price":INTEGER}
{"action":"reject"}
""".strip()

    user = f"""
Item: {item}
Seller reserve: {reserve}
Current asking price: {current_ask}
Buyer's latest offer: {buyer_offer}
Negotiation turn: {turn_number}

History:
{json.dumps(history)}

Choose the seller's next action.
""".strip()

    result = _call_json(
        system,
        user,
    )

    action = str(
        result.get("action", "")
    ).lower()

    # The model chooses the action.
    # Code only enforces the hard reserve boundary.
    if action == "accept":
        if buyer_offer < reserve:
            raise ValueError(
                "Harness attempted to accept below reserve."
            )

        return {
            "action": "accept",
        }

    if action == "counter":
        price = int(result["price"])

        if price < reserve:
            price = reserve

        return {
            "action": "counter",
            "price": price,
        }

    if action == "reject":
        return {
            "action": "reject",
        }

    raise ValueError(
        f"Unexpected seller decision: {result}"
    )


def buyer_turn(
    *,
    item: str,
    budget: int,
    seller_price: int,
    turn_number: int,
    history: list[str],
) -> dict[str, Any]:
    """
    Let the model choose the buyer's next offer
    or decide to walk away.
    """

    system = """
You are the decision-making harness for an A2A buyer.

You must decide every buyer offer and when to walk away.

Rules:
- The budget is the absolute maximum legal purchase price.
- Never offer more than the budget.
- Your goal is to successfully buy the item if the seller can reach your budget.
- If the seller's current price is within budget, you should normally offer that price to close the deal.
- If the seller price is above budget, negotiate upward toward the budget.
- Do not walk away too early if a deal still appears possible.
- Walk away when the seller cannot reach the budget.
- Use a whole-number offer.

Return ONLY one of these JSON objects:

{"action":"offer","price":INTEGER}
{"action":"walk"}
""".strip()

    user = f"""
Item: {item}
Buyer budget: {budget}
Seller's latest asking/counter price: {seller_price}
Negotiation turn: {turn_number}

History:
{json.dumps(history)}

Choose the buyer's next action.
""".strip()

    result = _call_json(
        system,
        user,
    )

    action = str(
        result.get("action", "")
    ).lower()

    if action == "offer":
        price = int(result["price"])

        # Safety enforcement in code as well as prompt.
        if price > budget:
            price = budget

        if price < 0:
            price = 0

        return {
            "action": "offer",
            "price": price,
        }

    if action == "walk":
        return {
            "action": "walk",
        }

    raise ValueError(
        f"Unexpected buyer decision: {result}"
    )


if __name__ == "__main__":
    print(
        json.dumps(
            {
                "provider": "GroqCloud",
                "model": MODEL,
                "base_url": BASE_URL,
                "status": "ready",
            },
            indent=2,
        )
    )