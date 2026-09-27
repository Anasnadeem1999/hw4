export interface ProductSummary {
  product_id: string
  name: string
  garment_type: string
  category: string
  short_description: string
  price: number
  image_url: string
  colors: string[]
  available_sizes: string[]
  in_stock: boolean
}

export interface SizeStock {
  size: string
  quantity: number
  in_stock: boolean
}

export interface ProductDetail extends ProductSummary {
  description: string
  search_tags: string[]
  sizes: SizeStock[]
  total_stock: number
}

export interface User {
  id: number
  name: string
  first_name: string | null
  last_name: string | null
  email: string
  created_at: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ProductCard {
  product_id: string
  name: string
  price: number
  image_url: string
  category: string
  short_description: string
  available_sizes: string[]
}

export interface ChatResponse {
  reply: string
  products: ProductCard[]
  tools_used: string[]
}
