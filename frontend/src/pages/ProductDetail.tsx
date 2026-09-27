import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, formatPrice } from '../api'
import { isMulticolor, swatchFor } from '../colors'
import type { ProductDetail as Product } from '../types'

const LOW_STOCK = 5

export default function ProductDetail() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [selectedSize, setSelectedSize] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setProduct(null)
    setSelectedSize(null)
    setError(null)
    fetchProduct(productId)
      .then(setProduct)
      .catch(() => setError('We could not find that product.'))
  }, [productId])

  if (error) {
    return (
      <div className="page state">
        <h2 className="state__title">Product not found</h2>
        <p>{error}</p>
        <p>
          <Link to="/products" className="section-link">
            Back to all products
          </Link>
        </p>
      </div>
    )
  }

  if (!product) {
    return (
      <div className="page section">
        <div className="skeleton" style={{ maxWidth: 520, aspectRatio: '4 / 3' }} />
      </div>
    )
  }

  const selected = product.sizes.find((s) => s.size === selectedSize)
  const availableCount = product.sizes.filter((s) => s.in_stock).length

  return (
    <section className="section">
      <div className="page">
        <p className="crumb">
          <Link to="/products">Products</Link>
          {' / '}
          <Link to={`/products?category=${encodeURIComponent(product.category)}`}>
            {product.category}
          </Link>
          {' / '}
          {product.name}
        </p>

        <div className="detail">
          <div className="detail__media">
            <img src={product.image_url} alt={product.name} />
          </div>

          <div>
            <p className="eyebrow">{product.garment_type}</p>
            <h1 className="detail__name">{product.name}</h1>
            <p className="detail__price">{formatPrice(product.price)}</p>
            <p className="detail__desc">{product.description}</p>

            <div className="field">
              <p className="field__label">
                Size {availableCount < product.sizes.length && `· ${availableCount} of ${product.sizes.length} in stock`}
              </p>
              <div className="sizes">
                {product.sizes.map((s) => (
                  <button
                    key={s.size}
                    className={`size ${selectedSize === s.size ? 'is-selected' : ''}`}
                    disabled={!s.in_stock}
                    onClick={() => setSelectedSize(s.size)}
                    title={s.in_stock ? `${s.quantity} in stock` : 'Out of stock'}
                  >
                    {s.size}
                    <span className="size__qty">
                      {s.in_stock ? `${s.quantity} left` : 'Sold out'}
                    </span>
                  </button>
                ))}
              </div>
              {selected && (
                <p
                  className={`stock-note ${selected.quantity <= LOW_STOCK ? 'stock-note--low' : ''}`}
                >
                  {selected.quantity <= LOW_STOCK
                    ? `Only ${selected.quantity} left in ${selected.size} — order soon.`
                    : `${selected.quantity} in stock in ${selected.size}.`}
                </p>
              )}
            </div>

            <div className="field">
              <p className="field__label">Colours</p>
              <div className="swatches">
                {product.colors.map((c) => (
                  <span key={c} className="swatch">
                    {isMulticolor(c) ? (
                      <span className="dot dot--multi" />
                    ) : (
                      <span className="dot" style={{ background: swatchFor(c) ?? '#ccc' }} />
                    )}
                    {c}
                  </span>
                ))}
              </div>
            </div>

            <div className="field">
              <p className="field__label">Details</p>
              <div className="swatches">
                <span className="swatch">{product.total_stock} units across all sizes</span>
                <span className="swatch">Officially licensed</span>
              </div>
            </div>

            <div className="field">
              <p className="field__label">Tags</p>
              <div className="tags">
                {product.search_tags.map((t) => (
                  <span key={t} className="tag">
                    {t}
                  </span>
                ))}
              </div>
            </div>

            <button className="button button--primary button--block" disabled={!selectedSize}>
              {selectedSize ? `Add ${selectedSize} to bag` : 'Select a size'}
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
