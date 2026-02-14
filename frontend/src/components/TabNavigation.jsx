/**
 * 标签导航组件
 * 优化说明：
 * 1. 添加 cursor-pointer 样式到按钮
 * 2. 添加平滑过渡动画（transition-colors duration-200）
 * 3. 优化无障碍性（aria-label, aria-selected）
 * 4. 添加键盘导航支持
 * 5. 使用 4 空格缩进
 */
import React from "react";

function TabNavigation({ tabs, activeTab, onTabChange }) {
  const handleKeyDown = (e, tabId) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onTabChange(tabId);
    }
  };

  return (
    <div className="tabs" role="tablist" aria-label="功能导航">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={`tab-button ${activeTab === tab.id ? "active" : ""}`}
          onClick={() => onTabChange(tab.id)}
          onKeyDown={(e) => handleKeyDown(e, tab.id)}
          role="tab"
          aria-selected={activeTab === tab.id}
          aria-label={tab.label}
          style={{
            cursor: "pointer",
            transition: "all 0.2s ease",
          }}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export default TabNavigation;
