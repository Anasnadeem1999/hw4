import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { ProductCard } from './types'

/**
 * Products the shopping assistant has matched, lifted out of the chat panel so
 * the page can render them too.
 *
 * The chat widget owns the conversation; this owns "what is currently being
 * shown because of it". Keeping them separate means the page section survives
 * closing the chat panel, which is the whole point — a shopper can collapse
 * the chat and still browse what it found.
 */
interface ChatResultsState {
  matches: ProductCard[]
  /** What the shopper asked that produced these matches, for the heading. */
  query: string | null
  setMatches: (products: ProductCard[], query: string) => void
  clear: () => void
}

const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [matches, setMatchesState] = useState<ProductCard[]>([])
  const [query, setQuery] = useState<string | null>(null)

  const setMatches = useCallback((products: ProductCard[], asked: string) => {
    // A turn that matched nothing leaves the previous results alone rather
    // than blanking the page — the shopper may still be looking at them.
    if (products.length === 0) return
    setMatchesState(products)
    setQuery(asked)
  }, [])

  const clear = useCallback(() => {
    setMatchesState([])
    setQuery(null)
  }, [])

  const value = useMemo(
    () => ({ matches, query, setMatches, clear }),
    [matches, query, setMatches, clear],
  )

  return <ChatResultsContext.Provider value={value}>{children}</ChatResultsContext.Provider>
}

export function useChatResults() {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside ChatResultsProvider')
  return ctx
}
