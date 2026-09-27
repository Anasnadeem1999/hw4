import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="page">
        <div className="footer__grid">
          <div>
            <h3 className="footer__title">Campus Customs</h3>
            <ul className="footer__list">
              <li>57 Broadway</li>
              <li>New Haven, CT 06511</li>
              <li>Open seven days a week</li>
            </ul>
          </div>
          <div>
            <h3 className="footer__title">Shop</h3>
            <ul className="footer__list">
              <li>
                <Link to="/products">All products</Link>
              </li>
              <li>
                <Link to="/products?category=T-Shirts">T-Shirts</Link>
              </li>
              <li>
                <Link to="/products?category=Crewnecks">Crewnecks</Link>
              </li>
              <li>
                <Link to="/products?category=Hoodies">Hoodies</Link>
              </li>
            </ul>
          </div>
          <div>
            <h3 className="footer__title">Account</h3>
            <ul className="footer__list">
              <li>
                <Link to="/login">Log in</Link>
              </li>
              <li>
                <Link to="/create-account">Create account</Link>
              </li>
            </ul>
          </div>
          <div>
            <h3 className="footer__title">About</h3>
            <ul className="footer__list">
              <li>
                <Link to="/about">Our story</Link>
              </li>
            </ul>
          </div>
        </div>
        <div className="footer__bottom">
          <span>© {new Date().getFullYear()} Campus Customs, New Haven</span>
          <span>A student project for Yale SOM MGT 409 — not a real storefront.</span>
        </div>
      </div>
    </footer>
  )
}
