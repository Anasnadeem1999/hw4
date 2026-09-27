import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts } from '../api'
import ProductCard from '../components/ProductCard'
import type { ProductSummary } from '../types'
import { useReveal } from '../useReveal'

const CATEGORY_LINKS = [
  { label: 'T-Shirts', blurb: 'Lightweight cotton for everyday wear' },
  { label: 'Crewnecks', blurb: 'The classic New Haven sweatshirt' },
  { label: 'Hoodies', blurb: 'Warm layers for a cold Elm Street walk' },
  { label: 'Quarter-Zips', blurb: 'A little more polish for game day' },
]

export default function Home() {
  const [featured, setFeatured] = useState<ProductSummary[]>([])

  useEffect(() => {
    fetchProducts()
      .then((all) => setFeatured(all.slice(0, 8)))
      .catch(() => setFeatured([]))
  }, [])

  useReveal([featured.length])

  return (
    <>
      <section className="hero">
        <div className="page">
          <div className="hero__inner">
            <p className="eyebrow">Campus Customs · New Haven</p>
            <h1 className="hero__title">
              Yale gear, straight from <em>Broadway</em>.
            </h1>
            <p className="hero__text">
              We have been outfitting students, families, and returning alumni from our
              shop on Broadway for decades. Every piece here is officially licensed Yale
              apparel, picked for the way people in New Haven actually dress — on the way
              to class, in the stands, or home for the holidays.
            </p>
            <div className="hero__actions">
              <Link to="/products" className="button">
                Shop all products
              </Link>
              <Link to="/about" className="button button--ghost">
                Our story
              </Link>
            </div>
          </div>

          <div className="hero__meta">
            <div>
              <p className="hero__stat-value">102</p>
              <p className="hero__stat-label">Pieces in stock</p>
            </div>
            <div>
              <p className="hero__stat-value">XS–XXL</p>
              <p className="hero__stat-label">Every style, every size</p>
            </div>
            <div>
              <p className="hero__stat-value">57</p>
              <p className="hero__stat-label">Broadway, New Haven</p>
            </div>
            <div>
              <p className="hero__stat-value">7 days</p>
              <p className="hero__stat-label">Open every week</p>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="page">
          <div className="section-head" data-reveal>
            <div>
              <p className="eyebrow">This week</p>
              <h2 className="section-title">Featured pieces</h2>
            </div>
            <Link to="/products" className="section-link">
              View all
            </Link>
          </div>
          <div className="grid">
            {featured.length === 0
              ? Array.from({ length: 8 }).map((_, i) => <div key={i} className="skeleton" />)
              : featured.map((p, i) => (
                  <div key={p.product_id} data-reveal style={{ ['--i' as string]: i }}>
                    <ProductCard product={p} />
                  </div>
                ))}
          </div>
        </div>
      </section>

      <section className="section section--band">
        <div className="page">
          <div className="section-head" data-reveal>
            <div>
              <p className="eyebrow">Find your thing</p>
              <h2 className="section-title">Shop by category</h2>
            </div>
          </div>
          <div className="fact-grid">
            {CATEGORY_LINKS.map((c, i) => (
              <Link
                key={c.label}
                to={`/products?category=${encodeURIComponent(c.label)}`}
                className="fact"
                data-reveal
                style={{ ['--i' as string]: i }}
              >
                <p className="fact__label">{c.blurb}</p>
                <p className="fact__value">{c.label} →</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="page prose" data-reveal>
          <p className="eyebrow">All year round</p>
          <h2 className="section-title">Bulldog blue, whatever the season</h2>
          <p style={{ marginTop: 18 }}>
            Our racks follow the Yale calendar. Tees and light layers when the campus
            fills up in September, heavier fleece once the weather turns, and plenty of
            navy in the run-up to The Game. Residential college and graduate school
            designs stay in stock year round, because someone is always looking for the
            one that says Saybrook, or Grace Hopper, or School of Management.
          </p>
          <p>
            Not sure which piece you want? Open the chat in the corner and describe what
            you are after — we can point you to something in your size.
          </p>
        </div>
      </section>
    </>
  )
}
