import type { ProductDetail, ProductSummary } from './types'

async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

export function fetchProducts(params: { category?: string; q?: string } = {}) {
  const search = new URLSearchParams()
  if (params.category) search.set('category', params.category)
  if (params.q) search.set('q', params.q)
  const qs = search.toString()
  return getJSON<ProductSummary[]>(`/api/products${qs ? `?${qs}` : ''}`)
}

export function fetchProduct(productId: string) {
  return getJSON<ProductDetail>(`/api/products/${encodeURIComponent(productId)}`)
}

export function fetchShopStats() {
  return getJSON<{ styles: number; units_in_stock: number }>('/api/stats')
}

export function fetchCategories() {
  return getJSON<string[]>('/api/categories')
}

export function formatPrice(price: number) {
  return `$${price.toFixed(2)}`
}
