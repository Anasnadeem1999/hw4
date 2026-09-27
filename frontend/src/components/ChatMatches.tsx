import { useChatResults } from '../chatResults'
import type { ProductSummary } from '../types'
import ProductCard from './ProductCard'

/**
 * The products the assistant found, shown on the page as ordinary product
 * cards — the same component the Products grid uses, so they look and behave
 * identically and clicking one opens the detail page.
 */
export default function ChatMatches() {
  const { matches, query, clear } = useChatResults()

  if (matches.length === 0) return null

  // ProductCard renders a ProductSummary. A chat ProductCard carries every
  // field it needs except the ones the grid does not show, so the shapes are
  // reconciled here rather than by giving ProductCard a second code path.
  const asSummaries: ProductSummary[] = matches.map((p) => ({
    product_id: p.product_id,
    name: p.name,
    garment_type: p.category,
    category: p.category,
    short_description: p.short_description,
    price: p.price,
    image_url: p.image_url,
    colors: [],
    available_sizes: p.available_sizes,
    in_stock: p.available_sizes.length > 0,
  }))

  return (
    <section className="section section--band chat-matches">
      <div className="page">
        <div className="section-head">
          <div>
            <p className="eyebrow">Picked out for you</p>
            <h2 className="section-title">From your chat</h2>
            {query && <p className="chat-matches__query">You asked: “{query}”</p>}
          </div>
          <button className="chat-matches__clear" onClick={clear}>
            Clear
          </button>
        </div>

        <div className="grid">
          {asSummaries.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      </div>
    </section>
  )
}
