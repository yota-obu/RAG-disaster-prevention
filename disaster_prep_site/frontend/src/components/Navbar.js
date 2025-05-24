import React from 'react';
import { Link } from 'react-router-dom';
import './Navbar.css'; // Optional: for styling the navbar

function Navbar() {
  return (
    <nav className="navbar">
      <ul className="navbar-nav">
        <li className="nav-item">
          <Link to="/" className="nav-link">防災備蓄シミュレータ</Link>
        </li>
        <li className="nav-item">
          <Link to="/chat" className="nav-link">防災Chat</Link>
        </li>
      </ul>
    </nav>
  );
}

export default Navbar;
