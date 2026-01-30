/**
 * AI客服悬浮按钮组件
 * 优化说明：
 * 1. 添加 cursor-pointer 样式
 * 2. 添加键盘导航支持（tabIndex, onKeyDown）
 * 3. 优化无障碍性（role, aria-label）
 * 4. 添加过渡动画提示
 */
import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import taifengGif from "../pictures/deepseek.png";
import "../styles/AIAgentButton.css";

function AIAgentButton() {
  const navigate = useNavigate();
  const location = useLocation();

  if (location.pathname === "/AI_agent") {
    return null;
  }

  const handleClick = () => {
    navigate("/AI_agent");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <div
      className="ai-agent-button"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-label="打开AI客服对话"
      style={{ cursor: "pointer" }}
    >
      <img src={taifengGif} alt="AI客服图标" />
      <div className="ai-agent-tooltip">AI客服</div>
    </div>
  );
}

export default AIAgentButton;
