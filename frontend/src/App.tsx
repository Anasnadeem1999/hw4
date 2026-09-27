import { Route, Routes, useMatch } from 'react-router-dom'
import ChatMatches from './components/ChatMatches'
import ChatWidget from './components/ChatWidget'
import Footer from './components/Footer'
import NavBar from './components/NavBar'
import About from './pages/About'
import CreateAccount from './pages/CreateAccount'
import Home from './pages/Home'
import Login from './pages/Login'
import ProductDetail from './pages/ProductDetail'
import Products from './pages/Products'

export default function App() {
  // On a product page the shopper is already looking at something specific, and
  // a results band above it would push that product below the fold. The chat
  // panel still lists the matches inline there.
  const onProductPage = useMatch('/products/:productId')

  return (
    <>
      <NavBar />
      <main>
        {!onProductPage && <ChatMatches />}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/create-account" element={<CreateAccount />} />
        </Routes>
      </main>
      <Footer />
      <ChatWidget />
    </>
  )
}
