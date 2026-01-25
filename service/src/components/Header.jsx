/**
 * 头部组件
 */
import React from "react";
import { headerLinks } from "../services/api";

function Header() {
  // 在开发环境使用相对路径（通过Vite代理），生产环境使用环境变量或默认后端地址
  const isDevelopment = import.meta.env.DEV;
  const API_BASE_URL = isDevelopment
    ? ""
    : import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"; // 生产环境使用完整URL

  return (
    <div className="header">
      <h1>🌀 台风路径可视化系统</h1>
      <div className="header-links">
        {headerLinks.map((link) => (
          <a
            key={link.id}
            href={`${API_BASE_URL}${link.path}`}
            target={link.target}
            rel={link.rel}
          >
            {link.label}
          </a>
        ))}
      </div>
    </div>
  );
}

export default Header;
