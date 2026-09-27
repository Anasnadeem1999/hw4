import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchCategories, fetchProducts } from '../api'
import ProductCard from '../components/ProductCard'
import type { ProductSummary } from '../types'
import { useReveal } from '../useReveal'

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

type Sort = 'name' | 'price-asc' | 'price-desc'

const SORTS: { value: Sort; label: string }[] = [
  { value: 'name', label: 'Name (A–Z)' },
  { value: 'price-asc', label: 'Price: low to high' },
  { value: 'price-desc', label: 'Price: high to low' },
]

export default function Products() {
  const [searchParams, setSearchParams] = useSearchParams()
  const category = searchParams.get('category') ?? ''

  const [categories, setCategories] = useState<string[]>([])
  const [products, setProducts] = useState<ProductSummary[]>([])
  const [query, setQuery] = useState('')
  const [size, setSize] = useState('')
  const [sort, setSort] = useState<Sort>('name')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchCategories().then(setCategories).catch(() => setCategories([]))
  }, [])

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchProducts({ category: category || undefined })
      .then(setProducts)
      .catch(() => setError('We could not load the catalogue. Is the backend running?'))
      .finally(() => setLoading(false))
  }, [category])

  function chooseCategory(next: string) {
    if (next) setSearchParams({ category: next })
    else setSearchParams({})
  }

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase()
    let list = products

    if (needle) {
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(needle) ||
          p.short_description.toLowerCase().includes(needle) ||
          p.colors.some((c) => c.includes(needle)),
      )
    }

    // Only products a shopper could actually buy in their size.
    if (size) {
      list = list.filter((p) => p.available_sizes.includes(size))
    }

    const sorted = [...list]
    if (sort === 'price-asc') sorted.sort((a, b) => a.price - b.price || a.name.localeCompare(b.name))
    else if (sort === 'price-desc') sorted.sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))
    else sorted.sort((a, b) => a.name.localeCompare(b.name))

    return sorted
  }, [products, query, size, sort])

  useReveal([visible.length])

  const hiddenBySize = size ? products.length - products.filter((p) => p.available_sizes.includes(size)).length : 0

  return (
    <section className="section">
      <div className="page">
        <div className="section-head">
          <div>
            <p className="eyebrow">Campus Customs</p>
            <h1 className="section-title">{category || 'All products'}</h1>
          </div>
          <span className="section-link" style={{ borderBottom: 'none' }}>
            {loading ? 'Loading…' : `${visible.length} item${visible.length === 1 ? '' : 's'}`}
          </span>
        </div>

        <div className="toolbar">
          <button
            className={`chip ${category === '' ? 'is-active' : ''}`}
            onClick={() => chooseCategory('')}
          >
            All
          </button>
          {categories.map((c) => (
            <button
              key={c}
              className={`chip ${category === c ? 'is-active' : ''}`}
              onClick={() => chooseCategory(c)}
            >
              {c}
            </button>
          ))}
          <div className="search">
            <input
              className="input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search products…"
              aria-label="Search products"
            />
          </div>
        </div>

        {/* Size availability and ordering — the two things a shopper actually
            wants control of once the category is chosen. */}
        <div className="toolbar toolbar--secondary">
          <span className="toolbar__label">My size</span>
          <button
            className={`chip chip--sm ${size === '' ? 'is-active' : ''}`}
            onClick={() => setSize('')}
          >
            Any
          </button>
          {SIZES.map((s) => (
            <button
              key={s}
              className={`chip chip--sm ${size === s ? 'is-active' : ''}`}
              onClick={() => setSize(size === s ? '' : s)}
            >
              {s}
            </button>
          ))}

          <label className="sort">
            <span className="toolbar__label">Sort</span>
            <select
              className="input input--select"
              value={sort}
              onChange={(e) => setSort(e.target.value as Sort)}
              aria-label="Sort products"
            >
              {SORTS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        {size && hiddenBySize > 0 && (
          <p className="filter-note">
            Showing only what is in stock in <strong>{size}</strong> — {hiddenBySize} item
            {hiddenBySize === 1 ? '' : 's'} hidden.
          </p>
        )}

        {error ? (
          <div className="state">
            <h2 className="state__title">Catalogue unavailable</h2>
            <p>{error}</p>
          </div>
        ) : loading ? (
          <div className="grid">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="skeleton" />
            ))}
          </div>
        ) : visible.length === 0 ? (
          <div className="state">
            <h2 className="state__title">Nothing matched</h2>
            <p>
              {size
                ? `We have nothing left in ${size} here. Try another size or category.`
                : 'Try a different search or category.'}
            </p>
          </div>
        ) : (
          <div className="grid">
            {visible.map((p, i) => (
              <div key={p.product_id} data-reveal style={{ ['--i' as string]: Math.min(i, 11) }}>
                <ProductCard product={p} />
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
