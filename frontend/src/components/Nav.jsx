import { Link, useLocation } from "react-router-dom";
export function Nav() {
  const location = useLocation();
  return (
    <nav className="nav">
      <Link to="/" className="nav-brand">LiveIndex</Link>
      <div className="nav-links">
        <Link to="/"        className={location.pathname === "/"        ? "active" : ""}>Cities</Link>
        <Link to="/compare" className={location.pathname === "/compare" ? "active" : ""}>Compare</Link>
      </div>
    </nav>
  );
}
