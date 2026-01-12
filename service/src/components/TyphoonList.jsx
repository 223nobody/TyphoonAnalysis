/**
 * 台风列表组件
 */
import React, { useState, useEffect } from "react";
import { getTyphoonList } from "../services/api";

function TyphoonList({ selectedTyphoons, onTyphoonSelect }) {
  const [typhoons, setTyphoons] = useState([]);
  const [filteredTyphoons, setFilteredTyphoons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 筛选条件
  const [filters, setFilters] = useState({
    year: "",
    search: "",
  });

  // 加载台风列表
  useEffect(() => {
    loadTyphoons();
  }, []);

  // 应用筛选
  useEffect(() => {
    applyFilters();
  }, [typhoons, filters]);

  const loadTyphoons = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getTyphoonList();

      // 修复：后端返回的是 data.items，不是 data.typhoons
      if (data && data.items && Array.isArray(data.items)) {
        setTyphoons(data.items);
      } else if (data && Array.isArray(data)) {
        // 兼容直接返回数组的情况
        setTyphoons(data);
      } else {
        console.error("API返回数据格式错误:", data);
        setError("加载台风列表失败：数据格式错误");
      }
    } catch (err) {
      console.error("加载台风列表失败:", err);
      setError(err.message || "加载失败，请检查后端服务是否正常运行");
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...typhoons];

    // 年份筛选
    if (filters.year) {
      filtered = filtered.filter((t) => t.year === parseInt(filters.year));
    }

    // 搜索筛选
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(
        (t) =>
          t.typhoon_id.toLowerCase().includes(searchLower) ||
          t.typhoon_name.toLowerCase().includes(searchLower) ||
          (t.typhoon_name_cn && t.typhoon_name_cn.includes(filters.search))
      );
    }

    setFilteredTyphoons(filtered);
  };

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleTyphoonClick = (typhoonId) => {
    onTyphoonSelect(typhoonId);
  };

  // 获取唯一年份列表
  const getYears = () => {
    const years = [...new Set(typhoons.map((t) => t.year))];
    return years.sort((a, b) => b - a);
  };

  if (loading) {
    return <div className="loading">加载台风列表中</div>;
  }

  if (error) {
    return (
      <div className="error-message">
        ❌ {error}
        <button
          className="btn"
          onClick={loadTyphoons}
          style={{ marginLeft: "10px" }}
        >
          重试
        </button>
      </div>
    );
  }

  return (
    <div>
      <h2>🌀 台风列表</h2>

      {/* 筛选表单 */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "15px",
          marginBottom: "20px",
        }}
      >
        <div className="form-group">
          <label>年份筛选</label>
          <select
            value={filters.year}
            onChange={(e) => handleFilterChange("year", e.target.value)}
          >
            <option value="">全部年份</option>
            {getYears().map((year) => (
              <option key={year} value={year}>
                {year}年
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>搜索台风</label>
          <input
            type="text"
            placeholder="输入台风ID或名称"
            value={filters.search}
            onChange={(e) => handleFilterChange("search", e.target.value)}
          />
        </div>
      </div>

      {/* 统计信息 */}
      <div className="info-card" style={{ marginBottom: "20px" }}>
        <p>
          <strong>总计:</strong> {typhoons.length} 个台风 |
          <strong> 筛选结果:</strong> {filteredTyphoons.length} 个 |
          <strong> 已选择:</strong> {selectedTyphoons.size} 个
        </p>
      </div>

      {/* 台风列表 */}
      {filteredTyphoons.length === 0 ? (
        <div style={{ textAlign: "center", padding: "40px", color: "#9ca3af" }}>
          未找到符合条件的台风
        </div>
      ) : (
        <div className="typhoon-list">
          {filteredTyphoons.map((typhoon) => (
            <div
              key={typhoon.typhoon_id}
              className={`typhoon-item ${
                selectedTyphoons.has(typhoon.typhoon_id) ? "selected" : ""
              }`}
              onClick={() => handleTyphoonClick(typhoon.typhoon_id)}
            >
              <div className="typhoon-item-header">
                <div className="typhoon-item-title">
                  {typhoon.typhoon_name_cn || typhoon.typhoon_name}
                </div>
                <div className="typhoon-item-id">{typhoon.typhoon_id}</div>
              </div>
              <div className="typhoon-item-info">
                <span>📅 {typhoon.year}年</span>
                <span>🌊 {typhoon.typhoon_name}</span>
                {typhoon.max_intensity && (
                  <span>💨 {typhoon.max_intensity}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default TyphoonList;
