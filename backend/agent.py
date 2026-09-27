"""PydanticAI agent wiring for the Campus Customs shopping assistant.

The agent is assembled here and nowhere else: the model comes from environment
configuration, the system prompt is read from `prompts/prompt.md`, and the
tools are the functions in `tools.py`.

Calls go through the course's Portkey gateway, which speaks the OpenAI
chat-completions protocol, so PydanticAI's OpenAI model class is pointed at
Portkey's base URL rather than at OpenAI directly.
"""

from __future__ import annotations

import os
import re
import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

import audit
import tools
from models import (
    MAX_HISTORY_REPLAYED,
    MAX_TOOL_CALLS,
    ChatDeps,
    ChatMessage,
    ChatResponse,
    clip,
)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "prompt.md"

MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-5.6-luna")
API_BASE_URL = os.environ.get("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
API_KEY = os.environ.get("PORTKEY_API_KEY")


def load_system_prompt() -> str:
    """Read the assistant's instructions from prompts/prompt.md.

    Kept as a file rather than a string literal so the shop's voice and safety
    rules can be edited without touching Python.
    """
    if not PROMPT_PATH.exists():
        raise RuntimeError(f"System prompt not found at {PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def build_agent() -> Agent[ChatDeps, str]:
    """Create the agent once and reuse it across requests."""
    if not API_KEY:
        raise RuntimeError(
            "PORTKEY_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    model = OpenAIChatModel(
        MODEL_NAME,
        provider=OpenAIProvider(base_url=API_BASE_URL, api_key=API_KEY),
    )

    agent = Agent(
        model,
        deps_type=ChatDeps,
        output_type=str,
        instructions=load_system_prompt(),
        retries=2,
    )

    # The tools are registered here rather than with decorators in tools.py so
    # that tools.py stays plain, testable functions.
    agent.tool(tools.search_products)
    agent.tool(tools.get_product_details)
    agent.tool(tools.get_price)
    agent.tool(tools.get_inventory)
    agent.tool(tools.check_size_availability)
    agent.tool(tools.list_categories)

    @agent.instructions
    def who_is_here(ctx) -> str:
        """Tell the agent who it is talking to.

        Built from the session cookie by the route, never from anything the
        model or the browser claimed, so this cannot be talked into naming a
        different shopper.
        """
        deps = ctx.deps
        if not deps.is_signed_in:
            return (
                "The shopper is browsing as a guest and is not signed in. "
                "You do not know their name. Do not ask for personal details; "
                "if they want their conversation remembered, they can create "
                "an account from the site header."
            )
        parts = [f"The shopper is signed in as {deps.user_name}"]
        if deps.user_email:
            parts.append(f"(account email: {deps.user_email})")
        return (
            " ".join(parts)
            + ". Greet them by their first name occasionally, not in every "
            "message. Their email is for your context only — do not read it "
            "back to them unless they ask you to confirm which account they "
            "are using."
        )

    @agent.instructions
    def where_they_are(ctx) -> str:
        """Tell the agent which page the shopper is looking at.

        This is what makes "do you have this in black?" resolvable — without
        it, "this" refers to nothing.
        """
        deps = ctx.deps
        if deps.page_product_id and deps.page_product_name:
            return (
                f"The shopper is currently looking at the product page for "
                f'"{deps.page_product_name}" (product_id: {deps.page_product_id}). '
                "If they say 'this', 'it', or 'this one' without naming a "
                "product, they mean that one — use that product_id with your "
                "tools rather than searching again."
            )
        if deps.page_path == "/products":
            return "The shopper is browsing the full product listing."
        if deps.page_path == "/":
            return "The shopper is on the home page."
        return "The shopper is browsing the site."

    return agent


# --------------------------------------------------------------------------
# Guardrail 1 — sensitive data in the shopper's message
# --------------------------------------------------------------------------
#
# A shopper who types a card number into a chat box has made a mistake, and the
# worst thing we could do is pass it to a model and then write it into
# chat_messages forever. This catches it before either happens.
#
# It also costs nothing: the turn is answered locally, with no model call.

_DIGIT_RUN = re.compile(r"(?:\d[ -]?){12,19}")
_SECRET_WORD = re.compile(
    r"\b(my (password|passcode|pin)\s*(is|:)|cvv|cvc|security code|"
    r"social security|sort code|routing number)\b",
    re.IGNORECASE,
)


def _luhn_ok(digits: str) -> bool:
    """Standard card checksum, so ordinary long numbers are not false flags."""
    total, parity = 0, len(digits) % 2
    for i, ch in enumerate(digits):
        n = int(ch)
        if i % 2 == parity:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def looks_sensitive(text: str) -> bool:
    """True if the message appears to contain payment or credential data."""
    if _SECRET_WORD.search(text):
        return True
    for match in _DIGIT_RUN.finditer(text):
        digits = re.sub(r"[ -]", "", match.group())
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            return True
    return False


SENSITIVE_REPLY = (
    "Please don't share card numbers, passwords, or similar details here — "
    "this chat isn't a secure place for them, and I have no way to take a "
    "payment. I've not kept what you just sent. If you'd like to buy "
    "something, you can order it on the product page or come by the shop at "
    "57 Broadway. Happy to help you find the right piece in the meantime."
)


# --------------------------------------------------------------------------
# Guardrail 2 — price figures in the reply must match the database
# --------------------------------------------------------------------------

_PRICE = re.compile(r"\$\s?(\d{1,4}(?:\.\d{1,2})?)")


def unverified_prices(reply: str, deps: ChatDeps) -> list[str]:
    """Dollar figures in the reply that match no product the agent looked up.

    The tools record every product they read into `deps.shown`, so their prices
    are exactly the set of figures the agent is entitled to quote. Anything else
    is either a hallucination or arithmetic we did not ask for.
    """
    allowed = {round(card.price, 2) for card in deps.shown.values()}
    # Sums of two shown products are common and legitimate ("both for $90").
    allowed |= {round(a + b, 2) for a in allowed for b in allowed}

    unknown: list[str] = []
    for match in _PRICE.finditer(reply):
        value = round(float(match.group(1)), 2)
        if value not in allowed:
            unknown.append(match.group())
    return unknown


def to_model_messages(history: list[ChatMessage]) -> list[dict]:
    """Convert the browser's history into PydanticAI message dicts."""
    return [{"role": m.role, "content": m.content} for m in history]




def redact(text: str) -> str:
    """Mask card-shaped digit runs before anything is written to disk.

    The audit trail records what the shopper asked, which for a blocked turn
    means the message that triggered the block. Writing that verbatim would
    store the card number we just refused to send to the model — the same
    mistake, in a different file. Digits are masked here so the trail still
    shows what happened without keeping the number.
    """
    return _DIGIT_RUN.sub(
        lambda m: "[redacted:" + str(len(re.sub(r"[ -]", "", m.group()))) + " digits]",
        text,
    )


def write_audit(
    deps: ChatDeps,
    message: str,
    response: ChatResponse,
    stop_reason: str,
    started: float,
) -> None:
    """Append one turn of the agent loop to the audit trail.

    Recorded whatever the outcome, including blocked and failed turns — a trail
    that only contains successes is not much of an audit.
    """
    audit.append(
        {
            "id": uuid.uuid4().hex[:12],
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "duration_ms": int((time.time() - started) * 1000),
            "model": MODEL_NAME,
            "shopper": (
                {"user_id": deps.user_id, "name": deps.user_name}
                if deps.is_signed_in
                else {"user_id": None, "name": "guest"}
            ),
            "page": {"path": deps.page_path, "product_id": deps.page_product_id},
            "message": clip(redact(message)),
            "tool_calls": [t.model_dump() for t in deps.tool_log],
            "tool_call_count": len(deps.tool_log),
            "tool_budget": MAX_TOOL_CALLS,
            "products_returned": [p.product_id for p in response.products],
            "price_guardrail_corrected": response.corrected,
            "stop_reason": stop_reason,
            "reply": clip(redact(response.reply), 400),
        }
    )


async def answer(
    message: str,
    history: list[ChatMessage] | None = None,
    deps: ChatDeps | None = None,
) -> ChatResponse:
    """Run one turn of the conversation and return the reply plus product cards.

    The cards come from `deps.shown`, which the tools fill in as they read the
    database — so every card corresponds to a row that was actually looked up,
    not to something the model wrote.

    `deps` carries who is chatting and what page they are on. The caller builds
    it from the session cookie and the request, so identity is never something
    the conversation can assert.
    """
    agent = build_agent()
    deps = deps or ChatDeps()
    started = time.time()

    # History is replayed as plain text context. Keeping it simple avoids
    # depending on PydanticAI's internal message format across versions.
    prior = ""
    if history:
        recent = history[-MAX_HISTORY_REPLAYED:]
        lines = [
            f"{'Shopper' if m.role == 'user' else 'You'}: {m.content}" for m in recent
        ]
        prior = "Earlier in this conversation:\n" + "\n".join(lines) + "\n\n"

    # Guardrail 1: payment or credential data never reaches the model, and is
    # never written to chat history. Answered locally, so it costs nothing.
    if looks_sensitive(message):
        response = ChatResponse(reply=SENSITIVE_REPLY, products=[], tools_used=[])
        write_audit(deps, message, response, "blocked_sensitive_input", started)
        return response

    result = await agent.run(f"{prior}Shopper: {message}", deps=deps)
    reply = result.output
    corrected = False
    stop_reason = "completed"

    # Guardrail 2: every dollar figure in the reply must belong to a product
    # the tools actually read. If one does not, give the model the real numbers
    # and let it rewrite — once. A second failure keeps the safer of the two
    # rather than looping.
    unknown = unverified_prices(reply, deps)
    if unknown and deps.shown:
        real = ", ".join(
            f"{card.name} is ${card.price:.2f}" for card in deps.shown.values()
        )
        retry = await agent.run(
            f"{prior}Shopper: {message}\n\n"
            f"[System correction: your draft reply quoted {', '.join(unknown)}, "
            f"which does not match the catalogue. The real prices are: {real}. "
            f"Rewrite your reply using only those figures, or leave prices out.]",
            deps=deps,
        )
        if not unverified_prices(retry.output, deps):
            reply = retry.output
            corrected = True
            stop_reason = "completed_after_price_correction"
        else:
            # The rewrite was no better; keep the first reply and say so in the
            # trail rather than pretending the check passed.
            stop_reason = "price_unverified_after_retry"

    if deps.budget_spent:
        stop_reason = "tool_budget_exhausted"

    response = ChatResponse(
        corrected=corrected,
        reply=reply,
        products=list(deps.shown.values()),
        tools_used=deps.tools_used,
    )
    write_audit(deps, message, response, stop_reason, started)
    return response
