/**
 * 标签导航组件
 */
import React from 'react';

function TabNavigation({ tabs, activeTab, onTabChange }) {
    return (
        <div className="tabs">
            {tabs.map((tab) => (
                <button
                    key={tab.id}
                    className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
                    onClick={() => onTabChange(tab.id)}
                >
                    {tab.label}
                </button>
            ))}
        </div>
    );
}

export default TabNavigation;

