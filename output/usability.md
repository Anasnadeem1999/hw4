# Usability Improvements — Campus Customs

Four improvements: two on the frontend, two on the agent and backend. I picked
them by looking at what the data actually looks like and where a shopper would
get stuck, rather than adding features for their own sake.

---

## Frontend 1 — Size availability shown on every product card

### What I added

Each product card in the grid now shows all six sizes, XS through XXL, with the
ones that are in stock highlighted and the sold-out ones greyed and struck
through. If a product is down to two sizes or fewer, a small "Only 2 sizes
left" flag sits on the image.

### Why it helps

When I analysed the database in Problem 2, I found that 145 of the 612
inventory rows are at zero, but not a single product is completely sold out.
That was the important detail. It means a normal "Sold out" badge would never
appear on our site, and a shopper would have no warning at all — every product
looks equally available from the grid.

So the real frustration here is not a product being gone, it is clicking into a
product, picking your size, and only then finding out it is not there. On our
data a quarter of size options would do that. Five products are down to just
two sizes.

Putting the sizes on the card moves that disappointment to before the click.
For the business it also does something useful: a shopper who can see that only
M and XL are left is far more likely to buy today than one who assumes it will
still be there next week.

---

## Frontend 2 — Filter by my size, and sort by price

### What I added

A second row of controls on the Products page. "My size" filters the grid down
to products that are actually in stock in that size, and a Sort dropdown orders
by price low to high, high to low, or name. When a size filter hides products,
the page says how many were hidden so it is clear what happened.

### Why it helps

We have 102 products and the only controls before this were a category filter
and a text search. If I wear a large, most of that grid is noise — 24 of the
102 products have no large in stock at all. Filtering by size turns browsing
into something that only shows me things I could genuinely buy.

Sorting by price matters because our range runs from $32 to $98, which is a
wide spread for a student. Someone shopping for a gift and someone buying a
cheap tee for the tailgate want opposite ends of that range, and neither could
get there before without scrolling the whole grid.

I deliberately did not add an "in stock only" toggle, even though it is the
obvious thing, because the data showed it would do nothing — no product is
fully out of stock, so the toggle would never filter anything. Filtering by
size is the version of that idea that actually works on our catalogue.

---

## Agent 1 — The chat refuses card numbers and passwords, and never stores them

### What I added

Before a message reaches the AI model, the backend checks whether it contains
payment or credential data. It looks for card-shaped numbers, validated with
the Luhn checksum so an ordinary long number is not flagged, and for phrases
like "my password is" or "CVV". If it finds either, the assistant answers
immediately with a warning, the message is never sent to the model, and it is
never written to the chat history table.

### Why it helps

People do type card numbers into chat boxes. They think they are checking out.
Our assistant cannot take a payment, so there is no upside at all to receiving
one, and two real downsides: the number goes to a third-party AI provider, and
it gets saved into `chat_messages` where it sits in the database indefinitely.

For a shop selling licensed university merchandise, storing a customer's card
number in a chat log is exactly the kind of thing that turns a small mistake
into a serious one. Catching it at the door means it never enters the system.

There is a side benefit I did not expect. Because these messages are answered
locally, they never cost an API call. The guarded reply comes back in about
0.13 seconds instead of the ten to twenty seconds a normal model call takes, so
the safest path is also the fastest and cheapest one.

I tested it while signed in, which is the case where the message would normally
have been saved. The row count did not move, and searching the table for the
card number returns nothing.

---

## Agent 2 — Every price the assistant quotes is checked against the database

### What I added

After the agent writes a reply but before the shopper sees it, the backend
pulls out every dollar figure in the text and compares it against the prices of
the products the agent actually looked up in that conversation. If a figure
does not belong to any of them, the agent is given the real prices and asked to
rewrite. It gets one attempt; if the rewrite is still wrong, we keep the
safer version rather than looping.

### Why it helps

The system prompt already tells the agent never to state a price from memory,
and in testing it followed that. But a prompt is an instruction, not a
guarantee. A wrong price is the single worst thing this chatbot could say — it
is the one mistake a customer will act on, turn up at 57 Broadway expecting,
and be annoyed about when it is not true. Telling someone a $68 hoodie is $40
is a promise the shop then has to either honour or break.

So this is a check that does not depend on the model behaving. The tools record
every product they read from the database, which means we know exactly which
prices the agent was entitled to quote. Anything else is either invented or
arithmetic nobody asked for, and it gets caught.

I allowed sums of two shown prices, because "both together would be $116" is
legitimate and I did not want the guardrail firing on correct maths. Tested
against a real reply, a correct $58 passes, an invented $49.99 is flagged, a
made-up $40 sale price is flagged, and a genuine $116 total passes.

---

## Where to see all four

| Improvement | Where |
|---|---|
| Size availability on cards | Products page, every card |
| Size filter and price sort | Products page, second toolbar row |
| Sensitive data guard | Chat widget — type a card-shaped number |
| Price fact-check | Chat widget — any reply quoting a price |
