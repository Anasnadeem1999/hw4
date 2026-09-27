import { Link } from 'react-router-dom'
import { formatPrice } from '../api'
import { isMulticolor, swatchFor } from '../colors'
import type { ProductSummary } from '../types'

const ALL_SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
const LOW_CHOICE = 2
const MAX_DOTS = 4

export default function ProductCard({ product }: { product: ProductSummary }) {
  const available = new Set(product.available_sizes)
  const dots = product.colors.slice(0, MAX_DOTS)
  const extraColors = product.colors.length - dots.length

  return (
    <Link to={`/products/${product.product_id}`} className="card">
      <div className="card__media">
        {available.size > 0 && available.size <= LOW_CHOICE && (
          <span className="card__flag">Only {available.size} sizes left</span>
        )}
        {available.size === 0 && <span className="card__flag card__flag--out">Sold out</span>}

        <img src={product.image_url} alt={product.name} loading="lazy" />

        {/* Sizes slide up on hover, so the grid stays calm but the answer is
            one gesture away. */}
        {product.available_sizes.length > 0 && (
          <span className="card__peek">
            <span className="card__peek-label">Sizes</span>
            {ALL_SIZES.map((size) => (
              <span
                key={size}
                className={available.has(size) ? 'size-pip' : 'size-pip is-out'}
                title={available.has(size) ? `${size} in stock` : `${size} sold out`}
              >
                {size}
              </span>
            ))}
          </span>
        )}
      </div>

      <h3 className="card__name">{product.name}</h3>

      <div className="card__row">
        <p className="card__price">{formatPrice(product.price)}</p>
        {dots.length > 0 && (
          <span className="swatch-row" aria-label={`Colours: ${product.colors.join(', ')}`}>
            {dots.map((c) =>
              isMulticolor(c) ? (
                <span key={c} className="dot dot--multi" title={c} />
              ) : (
                <span
                  key={c}
                  className="dot"
                  style={{ background: swatchFor(c) ?? '#ccc' }}
                  title={c}
                />
              ),
            )}
            {extraColors > 0 && <span className="dot--more">+{extraColors}</span>}
          </span>
        )}
      </div>

      <p className="card__desc">{product.short_description}</p>
    </Link>
  )
}
