/**
 * AI客服悬浮按钮组件
 */
import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import taifengGif from "../pictures/deepseek.png";
import "../styles/AIAgentButton.css";

function AIAgentButton() {
  const navigate = useNavigate();
  const location = useLocation();

  // 如果当前在AI客服页面，不显示悬浮按钮
  if (location.pathname === "/AI_agent") {
    return null;
  }

  const handleClick = () => {
    navigate("/AI_agent");
  };

  return (
    <div className="ai-agent-button" onClick={handleClick}>
      <img src={taifengGif} alt="AI客服" />
      <div className="ai-agent-tooltip">AI客服</div>
    </div>
  );
}

export default AIAgentButton;
