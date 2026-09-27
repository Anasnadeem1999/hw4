"""Structured types shared by the API, the agent, and its tools.

Anything the agent returns to the browser is described here, so the shape of a
chat response is defined in one place rather than assembled ad hoc in the route.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# Loop limits and result caps
# --------------------------------------------------------------------------
#
# These bound one turn of conversation. Without them a confused agent can loop
# on tools until it times out, and a single reply can drag the whole catalogue
# into the model context — slow for the shopper and expensive for the shop.

MAX_TOOL_CALLS = 8        # tool calls the agent may make in one turn
MAX_SEARCH_RESULTS = 8    # products a single search may return
MAX_HISTORY_REPLAYED = 10 # prior turns given back to the model
MAX_MESSAGE_CHARS = 2000  # length of one shopper message
MAX_HISTORY_TURNS = 40    # turns accepted in a request body
AUDIT_FIELD_CHARS = 200   # how much of an argument or result the audit keeps


def clip(text: str, limit: int = AUDIT_FIELD_CHARS) -> str:
    """Shorten a value for the audit trail."""
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


# --------------------------------------------------------------------------
# Catalogue types
# --------------------------------------------------------------------------


class ProductSummary(BaseModel):
    """A product as shown on the Products grid.

    `available_sizes` and `in_stock` are carried on the summary so the grid can
    show what is actually buyable without a request per card.
    """

    product_id: str
    name: str
    garment_type: str
    category: str
    short_description: str
    price: float
    image_url: str
    colors: list[str]
    available_sizes: list[str] = Field(default_factory=list)
    in_stock: bool = True


class SizeStock(BaseModel):
    size: str
    quantity: int
    in_stock: bool


class ProductDetail(ProductSummary):
    """A product as shown on its own detail page."""

    description: str
    search_tags: list[str]
    sizes: list[SizeStock]
    total_stock: int


# --------------------------------------------------------------------------
# Account types
# --------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: str
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    """What the frontend is allowed to see. Never includes the hash."""

    id: int
    name: str
    first_name: str | None
    last_name: str | None
    email: str
    created_at: str


# --------------------------------------------------------------------------
# Chat types
# --------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """One turn of the conversation, as the browser holds it."""

    role: Literal["user", "assistant"]
    content: str


class PageContext(BaseModel):
    """Where the shopper is on the site when they send a message.

    This is what lets "do you have this in black?" resolve. Without it the
    agent has only the words, and "this" points at nothing.
    """

    path: str | None = Field(default=None, max_length=300)
    product_id: str | None = Field(default=None, max_length=120)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # Guests carry their own history in the request, since nothing is saved for
    # them. For signed-in shoppers the server loads it from the database and
    # this is ignored.
    history: list[ChatMessage] = Field(default_factory=list, max_length=40)
    page: PageContext | None = None


class StoredChatMessage(BaseModel):
    """A saved turn, as returned when a signed-in shopper comes back."""

    role: Literal["user", "assistant"]
    content: str
    products: list["ProductCard"] = Field(default_factory=list)
    created_at: str


class ChatHistoryResponse(BaseModel):
    messages: list[StoredChatMessage] = Field(default_factory=list)


class ProductCard(BaseModel):
    """A product the agent referred to, rendered beside the reply.

    Deliberately assembled from database rows rather than from anything the
    model writes, so a card can never point at a product that does not exist.
    """

    product_id: str
    name: str
    price: float
    image_url: str
    category: str
    short_description: str
    available_sizes: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    products: list[ProductCard] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    corrected: bool = Field(
        default=False,
        description="True when the price guardrail rewrote the reply.",
    )


# --------------------------------------------------------------------------
# Agent tool results
# --------------------------------------------------------------------------
#
# These are what the *model* sees when a tool returns. They are kept narrow on
# purpose: the model needs enough to talk about a product, not every column.


class ProductSearchResult(BaseModel):
    """One hit from a catalogue search.

    Carries just enough for the model to talk about the product and decide
    whether it is worth recommending, without a second tool call: what it is
    (`name`, `category`, `description`), what it costs (`price`), what it looks
    like (`colors`), and what can actually be bought (`sizes_in_stock`).
    """

    product_id: str = Field(description="Stable id; pass this to the other tools.")
    name: str
    category: str
    price: float = Field(description="Dollars, read from catalogue.price.")
    colors: list[str]
    description: str
    sizes_in_stock: list[str] = Field(
        description="Only sizes with quantity > 0 right now."
    )


class SizeQuantity(BaseModel):
    """One row of the inventory table, as the model sees it."""

    size: str
    quantity: int
    in_stock: bool


class PriceInfo(BaseModel):
    """The answer to "how much is it?".

    Deliberately minimal. The model is told never to state a price from
    memory, so this exists to make the correct move cheap: one call, one
    number, nothing to misread.
    """

    product_id: str
    product_name: str
    price: float = Field(description="Dollars, read live from catalogue.price.")
    currency: str = "USD"


class InventoryReport(BaseModel):
    """Full stock picture for one product, every size.

    `sizes` is the complete run rather than only what is available, because a
    shopper asking "what sizes do you have" needs to hear which ones are gone
    as well as which are left. `sizes_in_stock` and `sizes_sold_out` are
    derived from it so the model does not have to filter the list itself and
    risk getting it backwards.
    """

    product_id: str
    product_name: str
    sizes: list[SizeQuantity]
    sizes_in_stock: list[str]
    sizes_sold_out: list[str]
    total_quantity: int = Field(description="Units on hand across every size.")
    any_in_stock: bool


class SizeAvailability(BaseModel):
    """The answer to "do you have it in M?".

    `in_stock` and `quantity` answer the question asked.
    `other_sizes_in_stock` is included so that a "no" can be useful — the model
    can offer the nearest real alternative in the same reply instead of
    prompting another round trip.
    """

    product_id: str
    product_name: str
    size: str
    in_stock: bool
    quantity: int = Field(description="Units of this exact size; 0 means sold out.")
    other_sizes_in_stock: list[str]


# --------------------------------------------------------------------------
# Agent dependencies
# --------------------------------------------------------------------------


class ToolCallRecord(BaseModel):
    """One tool call, as written to the audit trail.

    Arguments and results are stored as short summaries rather than in full:
    the trail is for answering "what did the agent do", not for duplicating the
    catalogue into a log file that grows without bound.
    """

    at: str
    tool: str
    args: str
    result: str
    ms: int


@dataclass
class ChatDeps:
    """Per-request state handed to the agent and its tools.

    `shown` is the bridge between the tools and the response: as tools look
    products up, they record the real rows here, and the route turns those into
    product cards. That is what keeps the cards honest — they come from the
    database lookups the agent actually performed, not from the reply text.

    The identity and page fields are filled in by the route from the session
    cookie and the request body, never by the model, so the agent cannot talk
    itself into being someone else.
    """

    # Who is chatting. All None for a guest.
    user_id: int | None = None
    user_first_name: str | None = None
    user_name: str | None = None
    user_email: str | None = None

    # Where they are on the site.
    page_path: str | None = None
    page_product_id: str | None = None
    page_product_name: str | None = None

    shown: dict[str, ProductCard] = field(default_factory=dict)
    tools_used: list[str] = field(default_factory=list)
    tool_log: list[ToolCallRecord] = field(default_factory=list)

    @property
    def is_signed_in(self) -> bool:
        return self.user_id is not None

    @property
    def budget_spent(self) -> bool:
        """True once the agent has used its tool-call budget for this turn."""
        return len(self.tool_log) >= MAX_TOOL_CALLS

    def log_tool(self, tool: str, args: str, result: str, ms: int) -> None:
        self.tool_log.append(
            ToolCallRecord(
                at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                tool=tool,
                args=clip(args),
                result=clip(result),
                ms=ms,
            )
        )

    def record(self, card: ProductCard, tool: str) -> None:
        self.shown.setdefault(card.product_id, card)
        if tool not in self.tools_used:
            self.tools_used.append(tool)
