import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? 'nav__link is-active' : 'nav__link'

export default function NavBar() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()

  async function signOut() {
    await logout()
    navigate('/')
  }

  return (
    <header className="header">
      <div className="header__bar">
        Officially licensed Yale apparel · 57 Broadway, New Haven · Open seven days
      </div>
      <div className="header__inner">
        <NavLink to="/" className="brand">
          <span className="brand__mark" aria-hidden>
            Y
          </span>
          <span>
            <span className="brand__name">Campus Customs</span>
            <span className="brand__tag">Yale Bulldog Blue</span>
          </span>
        </NavLink>

        <nav className="nav">
          <NavLink to="/" className={linkClass} end>
            Home
          </NavLink>
          <NavLink to="/products" className={linkClass}>
            Products
          </NavLink>
          <NavLink to="/about" className={linkClass}>
            About Us
          </NavLink>
          <span className="nav__divider" />

          {loading ? null : user ? (
            <>
              <span className="nav__user">Hi, {user.first_name || user.name.split(' ')[0]}</span>
              <button className="nav__signout" onClick={signOut}>
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className={linkClass}>
                Log in
              </NavLink>
              <NavLink to="/create-account" className="nav__cta">
                Create account
              </NavLink>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
