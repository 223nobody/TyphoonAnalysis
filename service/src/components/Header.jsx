/**
 * 头部组件
 */
import React from "react";

function Header() {
  return (
    <div className="header">
      <h1>🌀 台风路径可视化系统</h1>
      <div className="header-links">
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
        >
          📖 API文档
        </a>
        <a
          href="http://localhost:8000/health"
          target="_blank"
          rel="noopener noreferrer"
        >
          💚 系统状态
        </a>
      </div>
    </div>
  );
}

export default Header;
