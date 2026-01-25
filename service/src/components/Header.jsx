/**
 * 头部组件
 */
import React from "react";
import { headerLinks } from "../services/api";

function Header() {
  return (
    <div className="header">
      <h1>🌀 台风路径可视化系统</h1>
      <div className="header-links">
        {headerLinks.map((link) => (
          <a key={link.id} href={link.path} target={link.target} rel={link.rel}>
            {link.label}
          </a>
        ))}
      </div>
    </div>
  );
}

export default Header;
