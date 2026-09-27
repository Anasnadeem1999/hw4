import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useMatch } from 'react-router-dom'
import { formatPrice } from '../api'
import { useAuth } from '../auth'
import { useChatResults } from '../chatResults'
import type { ChatMessage, ProductCard } from '../types'

interface Turn extends ChatMessage {
  products?: ProductCard[]
}

const SUGGESTIONS = [
  'What shirts do you have?',
  'Something for The Game',
  'Saybrook crewneck in M?',
  'Anything under $40?',
]

const GREETING: Turn = {
  role: 'assistant',
  content:
    "Hi! I'm the Campus Customs shopping assistant. Ask me about sizes, prices, or what we have for your residential college.",
}

export default function ChatWidget() {
  const { user, loading: authLoading } = useAuth()
  const { setMatches } = useChatResults()
  const location = useLocation()
  // ChatWidget renders outside <Routes>, so useParams would be empty here.
  // useMatch reads the path directly and works anywhere under the router.
  const productMatch = useMatch('/products/:productId')
  const productId = productMatch?.params.productId

  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [turns, setTurns] = useState<Turn[]>([GREETING])
  const [busy, setBusy] = useState(false)
  const [restored, setRestored] = useState(false)
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [turns, open, busy])

  // Reload a signed-in shopper's saved conversation when they return. Guests
  // start fresh every time, which is the point of not saving theirs.
  useEffect(() => {
    if (authLoading) return
    if (!user) {
      setTurns([GREETING])
      setRestored(false)
      return
    }
    fetch('/api/chat/history', { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : { messages: [] }))
      .then((data) => {
        const saved: Turn[] = (data.messages ?? []).map(
          (m: { role: 'user' | 'assistant'; content: string; products: ProductCard[] }) => ({
            role: m.role,
            content: m.content,
            products: m.products,
          }),
        )
        if (saved.length > 0) {
          setTurns([GREETING, ...saved])
          setRestored(true)
        }
      })
      .catch(() => {
        /* a failed history load should not stop the shopper chatting */
      })
  }, [user, authLoading])

  async function clearHistory() {
    await fetch('/api/chat/history', { method: 'DELETE', credentials: 'include' })
    setTurns([GREETING])
    setRestored(false)
  }

  async function send(event: React.FormEvent) {
    event.preventDefault()
    await ask(draft)
  }

  async function ask(raw: string) {
    const message = raw.trim()
    if (!message || busy) return

    // Guests send their own history, since the server stores nothing for them.
    // For signed-in shoppers the server loads it and ignores this.
    const history = turns
      .filter((t) => t !== GREETING)
      .map(({ role, content }) => ({ role, content }))

    setTurns((prev) => [...prev, { role: 'user', content: message }])
    setDraft('')
    setBusy(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          history,
          // Page context: what the shopper is looking at as they ask.
          page: { path: location.pathname, product_id: productId ?? null },
        }),
        credentials: 'include', // so the agent knows who is signed in
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? 'The assistant is unavailable right now.')
      }
      const data = await res.json()
      setTurns((prev) => [
        ...prev,
        { role: 'assistant', content: data.reply, products: data.products },
      ])
      // Push the matches onto the page as full product cards.
      setMatches(data.products ?? [], message)
    } catch (err) {
      setTurns((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            err instanceof Error ? err.message : 'The assistant is unavailable right now.',
        },
      ])
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    return (
      <button className="chat-launcher" onClick={() => setOpen(true)}>
        <span className="chat-launcher__mark" aria-hidden>
          Y
        </span>
        Ask us anything
      </button>
    )
  }

  return (
    <section className="chat-panel" aria-label="Shopping assistant">
      <header className="chat-panel__head">
        <span className="chat-panel__mark" aria-hidden>
          Y
        </span>
        <div>
          <h2 className="chat-panel__title">Shopping Assistant</h2>
          <p className="chat-panel__sub">
            {user ? `Signed in as ${user.first_name ?? user.name}` : 'Chatting as a guest'}
          </p>
        </div>
        <button
          className="chat-panel__close"
          onClick={() => setOpen(false)}
          aria-label="Close chat"
        >
          ×
        </button>
      </header>

      {user && restored && (
        <div className="chat-restored">
          Picking up where you left off.
          <button onClick={clearHistory}>Start over</button>
        </div>
      )}

      {!user && (
        <div className="chat-restored chat-restored--guest">
          Chatting as a guest — this conversation is not saved.{' '}
          <Link to="/create-account" onClick={() => setOpen(false)}>
            Create an account
          </Link>
        </div>
      )}

      <div className="chat-log" ref={logRef}>
        {turns.map((turn, i) => (
          <div key={i} className="turn">
            <div className={`bubble bubble--${turn.role === 'user' ? 'user' : 'bot'}`}>
              {turn.content}
            </div>
            {turn.products && turn.products.length > 0 && (
              <div className="chat-cards">
                {turn.products.map((p) => (
                  <Link
                    key={p.product_id}
                    to={`/products/${p.product_id}`}
                    className="chat-card"
                    onClick={() => setOpen(false)}
                  >
                    <img src={p.image_url} alt={p.name} loading="lazy" />
                    <div className="chat-card__body">
                      <span className="chat-card__name">{p.name}</span>
                      <span className="chat-card__price">{formatPrice(p.price)}</span>
                      <span className="chat-card__sizes">
                        {p.available_sizes.length > 0
                          ? p.available_sizes.join(' · ')
                          : 'Sold out'}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        ))}

        {busy && (
          <div className="bubble bubble--bot bubble--typing" aria-live="polite">
            <span className="dot-t" />
            <span className="dot-t" />
            <span className="dot-t" />
          </div>
        )}
      </div>

      {turns.filter((t) => t.role === 'user').length === 0 && (
        <div className="chat-suggestions">
          {SUGGESTIONS.map((s) => (
            <button key={s} className="chat-suggestion" onClick={() => ask(s)} disabled={busy}>
              {s}
            </button>
          ))}
        </div>
      )}

      <form className="chat-form" onSubmit={send}>
        <input
          className="input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={productId ? 'Ask about this product…' : 'Ask about a product…'}
          aria-label="Message"
          disabled={busy}
        />
        <button className="chat-send" type="submit" disabled={!draft.trim() || busy}>
          Send
        </button>
      </form>
    </section>
  )
}
