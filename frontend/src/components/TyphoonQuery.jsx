/**
 * 台风数据查询组件
 */
import React, { useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import ReactECharts from "echarts-for-react";
import { message } from "antd";
import {
  getTyphoonList,
  getTyphoonById,
  getCrawlerStatus,
  getCrawlerLogs,
  getTyphoonPath,
} from "../services/api";
import "../styles/TyphoonQuery.css";
import "../styles/common.css";

function TyphoonQuery() {
  const [searchParams] = useSearchParams();
  const urlTyphoonId = searchParams.get("typhoon_id");

  // 使用ref跟踪是否已经处理过URL参数，避免重复处理
  const hasProcessedUrlTyphoonId = useRef(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // 爬虫相关状态
  const [crawlerData, setCrawlerData] = useState(null);
  const [crawlerLoading, setCrawlerLoading] = useState(false);

  // 台风列表查询表单
  const [listForm, setListForm] = useState({
    year: "",
    status: "",
  });

  // 台风详情查询表单
  const [detailForm, setDetailForm] = useState({
    typhoonId: "",
  });

  // 下拉选择器状态
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [dropdownTyphoons, setDropdownTyphoons] = useState([]);
  const [dropdownLoading, setDropdownLoading] = useState(false);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [availableYears, setAvailableYears] = useState([]);
  const [displayText, setDisplayText] = useState(""); // 用于输入框显示的文本

  // 处理台风列表查询
  const handleListQuery = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getTyphoonList();

      // 根据表单筛选
      let filteredData = data.items || [];
      if (listForm.year) {
        filteredData = filteredData.filter(
          (t) => t.year === parseInt(listForm.year),
        );
      }
      if (listForm.status !== "") {
        filteredData = filteredData.filter(
          (t) => t.status === parseInt(listForm.status),
        );
      }

      setResult({ type: "list", data: filteredData });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 处理台风详情查询 - 同时获取路径数据以计算统计信息
  const handleDetailQuery = async (specificTyphoonId = null) => {
    const typhoonIdToQuery = specificTyphoonId || detailForm.typhoonId;

    if (!typhoonIdToQuery) {
      alert("请输入台风ID");
      return;
    }

    console.log(`🔍 开始查询台风详情: ${typhoonIdToQuery}`);

    try {
      setLoading(true);
      setError(null);

      // 同时获取台风详情和路径数据
      const [detailData, pathData] = await Promise.all([
        getTyphoonById(typhoonIdToQuery),
        getTyphoonPath(typhoonIdToQuery).catch(() => ({ items: [] })),
      ]);

      console.log(`✅ 台风详情数据加载成功:`, detailData);
      console.log(
        `✅ 台风路径数据加载成功，路径点数量:`,
        (pathData.items || pathData || []).length,
      );

      // 从路径数据中计算统计信息
      const pathPoints = pathData.items || pathData || [];
      if (pathPoints.length > 0) {
        // 计算最大风速
        const windSpeeds = pathPoints
          .map((p) => p.max_wind_speed || p.wind_speed)
          .filter((v) => v != null);
        if (windSpeeds.length > 0 && !detailData.max_wind_speed) {
          detailData.max_wind_speed = Math.max(...windSpeeds);
        }

        // 计算最低气压
        const pressures = pathPoints
          .map((p) => p.center_pressure || p.pressure)
          .filter((v) => v != null);
        if (pressures.length > 0 && !detailData.min_pressure) {
          detailData.min_pressure = Math.min(...pressures);
        }

        // 计算最大强度（取最强的强度等级）
        const intensities = pathPoints
          .map((p) => p.intensity)
          .filter((v) => v != null);
        if (intensities.length > 0 && !detailData.max_intensity) {
          // 强度等级优先级
          const intensityOrder = [
            "超强台风",
            "强台风",
            "台风",
            "强热带风暴",
            "热带风暴",
            "热带低压",
          ];
          for (const level of intensityOrder) {
            if (intensities.includes(level)) {
              detailData.max_intensity = level;
              break;
            }
          }
        }

        // 计算起始时间和结束时间
        const timestamps = pathPoints
          .map((p) => p.timestamp || p.record_time || p.time)
          .filter((v) => v != null)
          .map((v) => new Date(v).getTime())
          .sort((a, b) => a - b);

        if (timestamps.length > 0) {
          if (!detailData.start_time) {
            detailData.start_time = new Date(timestamps[0]).toISOString();
          }
          if (!detailData.end_time) {
            detailData.end_time = new Date(
              timestamps[timestamps.length - 1],
            ).toISOString();
          }
        }
      }

      // 注意:查询台风详情不会记录查询历史
      // 查询历史仅在地图可视化页面查询台风路径时记录(MapVisualization.jsx)

      setResult({ type: "detail", data: detailData });
      setDropdownOpen(false); // 查询成功后关闭下拉框
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 加载下拉选择器的台风列表
  const loadDropdownTyphoons = async (year) => {
    try {
      setDropdownLoading(true);
      const params = year ? { year: parseInt(year) } : {};
      const data = await getTyphoonList(params);
      const typhoons = data.items || data || [];
      setDropdownTyphoons(typhoons);
    } catch (err) {
      console.error("加载台风列表失败:", err);
      setDropdownTyphoons([]);
    } finally {
      setDropdownLoading(false);
    }
  };

  // 加载可用年份列表
  const loadAvailableYears = async () => {
    try {
      const data = await getTyphoonList();
      const typhoons = data.items || data || [];
      const years = new Set();
      typhoons.forEach((t) => {
        if (t.year) years.add(t.year);
      });
      // 添加年份范围：2000 到 2026
      for (let year = 2000; year <= 2026; year++) {
        years.add(year);
      }
      setAvailableYears(Array.from(years).sort((a, b) => b - a));
    } catch (err) {
      console.error("加载年份列表失败:", err);
    }
  };

  // 初始化：加载年份列表
  React.useEffect(() => {
    loadAvailableYears();
  }, []);

  // 处理URL参数中的typhoon_id - 自动填充表单并触发查询
  React.useEffect(() => {
    if (urlTyphoonId && !hasProcessedUrlTyphoonId.current) {
      // 验证typhoon_id格式
      if (!urlTyphoonId || urlTyphoonId.trim() === "") {
        message.error("台风ID格式错误");
        hasProcessedUrlTyphoonId.current = true;
        return;
      }

      // 从typhoon_id中提取年份（假设格式为YYNNNN，如2501表示2025年01号台风）
      const typhoonIdStr = String(urlTyphoonId);
      if (typhoonIdStr.length >= 2) {
        const yearPrefix = typhoonIdStr.substring(0, 2);
        const targetYear = parseInt("20" + yearPrefix);

        if (!isNaN(targetYear) && targetYear >= 2000 && targetYear <= 2099) {
          console.log(`📅 从typhoon_id提取年份: ${targetYear}`);
          setSelectedYear(targetYear);
        }
      }

      // 先获取台风详情和路径数据，构建组合格式的displayText
      const loadTyphoonAndDisplay = async () => {
        try {
          // 同时获取台风详情和路径数据
          const [detailData, pathData] = await Promise.all([
            getTyphoonById(urlTyphoonId),
            getTyphoonPath(urlTyphoonId).catch(() => ({ items: [] })),
          ]);

          console.log(`✅ 台风详情数据加载成功:`, detailData);
          console.log(
            `✅ 台风路径数据加载成功，路径点数量:`,
            (pathData.items || pathData || []).length,
          );

          // 从路径数据中计算统计信息
          const pathPoints = pathData.items || pathData || [];
          if (pathPoints.length > 0) {
            // 计算最大风速
            const windSpeeds = pathPoints
              .map((p) => p.max_wind_speed || p.wind_speed)
              .filter((v) => v != null);
            if (windSpeeds.length > 0 && !detailData.max_wind_speed) {
              detailData.max_wind_speed = Math.max(...windSpeeds);
            }

            // 计算最低气压
            const pressures = pathPoints
              .map((p) => p.center_pressure || p.pressure)
              .filter((v) => v != null);
            if (pressures.length > 0 && !detailData.min_pressure) {
              detailData.min_pressure = Math.min(...pressures);
            }

            // 计算最大强度（取最强的强度等级）
            const intensities = pathPoints
              .map((p) => p.intensity)
              .filter((v) => v != null);
            if (intensities.length > 0 && !detailData.max_intensity) {
              const intensityOrder = [
                "超强台风",
                "强台风",
                "台风",
                "强热带风暴",
                "热带风暴",
                "热带低压",
              ];
              for (const level of intensityOrder) {
                if (intensities.includes(level)) {
                  detailData.max_intensity = level;
                  break;
                }
              }
            }

            // 计算起始时间和结束时间
            const timestamps = pathPoints
              .map((p) => p.timestamp || p.record_time || p.time)
              .filter((v) => v != null)
              .map((v) => new Date(v).getTime())
              .sort((a, b) => a - b);

            if (timestamps.length > 0) {
              if (!detailData.start_time) {
                detailData.start_time = new Date(timestamps[0]).toISOString();
              }
              if (!detailData.end_time) {
                detailData.end_time = new Date(
                  timestamps[timestamps.length - 1],
                ).toISOString();
              }
            }
          }

          // 填充表单
          setDetailForm({ typhoonId: urlTyphoonId });

          // 构建组合格式的显示文本：台风ID - 英文名 - 中文名
          const displayName = `${urlTyphoonId} - ${detailData.typhoon_name || "暂无"}${
            detailData.typhoon_name_cn ? ` - ${detailData.typhoon_name_cn}` : ""
          }`;
          setDisplayText(displayName);

          // 设置查询结果
          setResult({ type: "detail", data: detailData });

          hasProcessedUrlTyphoonId.current = true;
        } catch (err) {
          console.error(`❌ 获取台风详情失败:`, err);
          // 如果获取详情失败，只显示台风ID
          setDetailForm({ typhoonId: urlTyphoonId });
          setDisplayText(urlTyphoonId);
          // 仍然触发查询
          handleDetailQuery(urlTyphoonId);
          hasProcessedUrlTyphoonId.current = true;
        }
      };

      loadTyphoonAndDisplay();
    }
  }, [urlTyphoonId]);

  // 当选择年份改变时，加载对应年份的台风列表
  React.useEffect(() => {
    if (dropdownOpen) {
      loadDropdownTyphoons(selectedYear);
    }
  }, [selectedYear, dropdownOpen]);

  // 当URL参数变化时，重置处理标志
  React.useEffect(() => {
    hasProcessedUrlTyphoonId.current = false;
  }, [urlTyphoonId]);

  // 处理输入框点击，打开下拉选择器
  const handleInputFocus = () => {
    setDropdownOpen(true);
    if (dropdownTyphoons.length === 0) {
      loadDropdownTyphoons(selectedYear);
    }
  };

  // 处理台风卡片点击
  const handleTyphoonCardClick = (typhoon) => {
    // 确保typhoonId是字符串
    const typhoonId = String(typhoon.typhoon_id);

    // 只存储台风ID用于查询
    setDetailForm({ typhoonId: typhoonId });

    // 构建显示文本：台风ID - 英文名 - 中文名
    const displayName = `${typhoonId} - ${typhoon.typhoon_name}${
      typhoon.typhoon_name_cn ? ` - ${typhoon.typhoon_name_cn}` : ""
    }`;
    setDisplayText(displayName);

    setDropdownOpen(false);
  };

  // 处理点击外部区域关闭下拉框
  React.useEffect(() => {
    const handleClickOutside = (event) => {
      const dropdown = document.querySelector(".typhoon-dropdown-container");
      if (dropdown && !dropdown.contains(event.target)) {
        setDropdownOpen(false);
      }
    };

    if (dropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [dropdownOpen]);

  // 处理台风路径查询
  const handlePathQuery = async () => {
    if (!detailForm.typhoonId) {
      alert("请输入台风ID");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      console.log(`🔍 开始查询台风路径: ${detailForm.typhoonId}`);
      const data = await getTyphoonPath(detailForm.typhoonId);
      const pathData = data.items || data || [];
      setResult({ type: "path", data: pathData });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 获取爬虫状态
  const handleGetCrawlerStatus = async () => {
    try {
      setCrawlerLoading(true);
      const data = await getCrawlerStatus();
      setCrawlerData({ type: "status", data });
    } catch (err) {
      setError(err.message);
    } finally {
      setCrawlerLoading(false);
    }
  };

  // 获取爬虫日志
  const handleGetCrawlerLogs = async () => {
    try {
      setCrawlerLoading(true);
      const data = await getCrawlerLogs();
      setCrawlerData({ type: "logs", data });
    } catch (err) {
      setError(err.message);
    } finally {
      setCrawlerLoading(false);
    }
  };

  // 渲染台风列表表单
  const renderListForm = () => (
    <div>
      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px" }}
      >
        <div className="form-group">
          <label>年份（可选）</label>
          <input
            type="number"
            placeholder="例如: 2025"
            value={listForm.year}
            onChange={(e) => setListForm({ ...listForm, year: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label>状态（可选）</label>
          <select
            value={listForm.status}
            onChange={(e) =>
              setListForm({ ...listForm, status: e.target.value })
            }
          >
            <option value="">全部</option>
            <option value="1">活跃</option>
            <option value="0">已停止</option>
          </select>
        </div>
      </div>
      <button className="btn" onClick={handleListQuery} disabled={loading}>
        🔍 查询台风列表
      </button>
    </div>
  );

  // 渲染台风详情表单 - 带下拉选择器
  const renderDetailForm = () => (
    <div>
      <div className="form-group typhoon-dropdown-container">
        <label>台风ID</label>
        <input
          type="text"
          placeholder="点击选择台风或输入台风ID"
          value={displayText || detailForm.typhoonId}
          onChange={(e) => {
            const value = e.target.value;
            // 用户手动输入时，清空displayText，只保留typhoonId
            setDisplayText("");
            setDetailForm({ ...detailForm, typhoonId: value });
          }}
          onFocus={handleInputFocus}
          style={{ cursor: "pointer" }}
        />

        {/* 下拉选择面板 */}
        {dropdownOpen && (
          <div className="typhoon-dropdown-panel">
            <div className="dropdown-content">
              {/* 左侧：年份选择列表 */}
              <div className="dropdown-years">
                <h4>选择年份</h4>
                <div className="year-list">
                  {availableYears.map((year) => (
                    <div
                      key={year}
                      className={`year-item ${
                        selectedYear === year ? "active" : ""
                      }`}
                      onClick={() => setSelectedYear(year)}
                    >
                      {year}年
                    </div>
                  ))}
                </div>
              </div>

              {/* 右侧：台风卡片列表 */}
              <div className="dropdown-typhoons">
                <h4>{selectedYear}年台风列表</h4>
                {dropdownLoading ? (
                  <div className="dropdown-loading">加载中...</div>
                ) : dropdownTyphoons.length === 0 ? (
                  <div className="dropdown-empty">暂无台风数据</div>
                ) : (
                  <div className="typhoon-cards">
                    {dropdownTyphoons.map((typhoon) => (
                      <div
                        key={typhoon.typhoon_id}
                        className="typhoon-card"
                        onClick={() => handleTyphoonCardClick(typhoon)}
                      >
                        <div className="card-header">
                          <div className="card-title">
                            {typhoon.typhoon_name_cn || typhoon.typhoon_name}
                          </div>
                          <div className="card-id">{typhoon.typhoon_id}</div>
                        </div>
                        <div className="card-info">
                          <span>🌊 {typhoon.typhoon_name}</span>
                          <span
                            className={`status-badge ${
                              typhoon.status === 1 ? "active" : "inactive"
                            }`}
                          >
                            {typhoon.status === 1 ? "活跃" : "已停止"}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      <div style={{ display: "flex", gap: "10px" }}>
        <button
          className="btn"
          onClick={() => handleDetailQuery()}
          disabled={loading}
        >
          🔍 查询台风详情
        </button>
        <button
          className="btn"
          onClick={() => handlePathQuery()}
          disabled={loading}
        >
          🗺️ 查询台风路径
        </button>
      </div>
    </div>
  );

  // 渲染台风列表结果
  const renderListResult = (data) => {
    if (!data || data.length === 0) {
      return (
        <div className="info-card" style={{ marginTop: "20px" }}>
          <p>未找到符合条件的台风</p>
        </div>
      );
    }

    return (
      <div className="info-card" style={{ marginTop: "20px" }}>
        <h4>📋 台风列表（共 {data.length} 个）</h4>
        <table>
          <thead>
            <tr>
              <th>台风ID</th>
              <th>中文名</th>
              <th>英文名</th>
              <th>年份</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            {data.map((typhoon) => (
              <tr key={typhoon.typhoon_id}>
                <td style={{ textAlign: "center" }}>{typhoon.typhoon_id}</td>
                <td>{typhoon.typhoon_name_cn || "暂无数据"}</td>
                <td>{typhoon.typhoon_name || "暂无数据"}</td>
                <td style={{ textAlign: "center" }}>{typhoon.year}</td>
                <td style={{ textAlign: "center" }}>
                  <span
                    style={{
                      color: typhoon.status === 1 ? "#10b981" : "#6b7280",
                      fontWeight: "bold",
                    }}
                  >
                    {typhoon.status === 1 ? "活跃" : "已停止"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  // 渲染台风详情结果 - 优化为表格形式
  const renderDetailResult = (data) => {
    if (!data) {
      return (
        <div className="info-card" style={{ marginTop: "20px" }}>
          <p>未找到该台风</p>
        </div>
      );
    }

    return (
      <div className="info-card" style={{ marginTop: "20px" }}>
        <h4>🌀 台风详情</h4>
        <div style={{ overflowX: "auto" }}>
          <table className="detail-table">
            <tbody>
              <tr>
                <td>
                  <strong>台风ID</strong>
                </td>
                <td>{data.typhoon_id}</td>
              </tr>
              <tr>
                <td>
                  <strong>中文名</strong>
                </td>
                <td>{data.typhoon_name_cn || "暂无数据"}</td>
              </tr>
              <tr>
                <td>
                  <strong>英文名</strong>
                </td>
                <td>{data.typhoon_name || "暂无数据"}</td>
              </tr>
              <tr>
                <td>
                  <strong>年份</strong>
                </td>
                <td>{data.year}</td>
              </tr>
              <tr>
                <td>
                  <strong>状态</strong>
                </td>
                <td>
                  <span
                    style={{
                      color: data.status === 1 ? "#10b981" : "#6b7280",
                      fontWeight: "bold",
                    }}
                  >
                    {data.status === 1 ? "活跃" : "已停止"}
                  </span>
                </td>
              </tr>
              <tr>
                <td>
                  <strong>最大风速</strong>
                </td>
                <td>
                  {data.max_wind_speed
                    ? `${data.max_wind_speed} m/s`
                    : "暂无数据"}
                </td>
              </tr>
              <tr>
                <td>
                  <strong>最低气压</strong>
                </td>
                <td>
                  {data.min_pressure ? `${data.min_pressure} hPa` : "暂无数据"}
                </td>
              </tr>
              <tr>
                <td>
                  <strong>最大强度</strong>
                </td>
                <td>{data.max_intensity || "暂无数据"}</td>
              </tr>
              <tr>
                <td>
                  <strong>起始时间</strong>
                </td>
                <td>
                  {data.start_time
                    ? new Date(data.start_time).toLocaleString("zh-CN")
                    : data.created_at
                      ? new Date(data.created_at).toLocaleString("zh-CN")
                      : "暂无数据"}
                </td>
              </tr>
              <tr>
                <td>
                  <strong>结束时间</strong>
                </td>
                <td>
                  {data.end_time
                    ? new Date(data.end_time).toLocaleString("zh-CN")
                    : data.updated_at
                      ? new Date(data.updated_at).toLocaleString("zh-CN")
                      : "暂无数据"}
                </td>
              </tr>
              <tr>
                <td>
                  <strong>起始位置</strong>
                </td>
                <td>
                  {data.start_location ? (
                    <div>
                      <div>
                        经度: {data.start_location.longitude?.toFixed(2)}°,
                        纬度: {data.start_location.latitude?.toFixed(2)}°
                      </div>
                    </div>
                  ) : (
                    "暂无数据"
                  )}
                </td>
              </tr>
              <tr>
                <td>
                  <strong>结束位置</strong>
                </td>
                <td>
                  {data.end_location ? (
                    <div>
                      <div>
                        经度: {data.end_location.longitude?.toFixed(2)}°, 纬度:{" "}
                        {data.end_location.latitude?.toFixed(2)}°
                      </div>
                    </div>
                  ) : (
                    "暂无数据"
                  )}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // 渲染搜索结果
  const renderSearchResult = (data) => {
    if (!data || data.length === 0) {
      return (
        <div className="info-card" style={{ marginTop: "20px" }}>
          <p>未找到符合条件的台风</p>
        </div>
      );
    }

    return (
      <div className="info-card" style={{ marginTop: "20px" }}>
        <h4>🔍 搜索结果（共 {data.length} 个）</h4>
        <table>
          <thead>
            <tr>
              <th>台风ID</th>
              <th>中文名</th>
              <th>英文名</th>
              <th>年份</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            {data.map((typhoon) => (
              <tr key={typhoon.typhoon_id}>
                <td style={{ textAlign: "center" }}>{typhoon.typhoon_id}</td>
                <td>{typhoon.typhoon_name_cn || "暂无数据"}</td>
                <td>{typhoon.typhoon_name || "暂无数据"}</td>
                <td style={{ textAlign: "center" }}>{typhoon.year}</td>
                <td style={{ textAlign: "center" }}>
                  <span
                    style={{
                      color: typhoon.status === 1 ? "#10b981" : "#6b7280",
                      fontWeight: "bold",
                    }}
                  >
                    {typhoon.status === 1 ? "活跃" : "已停止"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  // 渲染台风路径结果 - 修复字段名映射，参考index.html，显示全部路径点
  const renderPathResult = (data) => {
    if (!data || data.length === 0) {
      return (
        <div className="info-card" style={{ marginTop: "20px" }}>
          <p>未找到该台风的路径数据</p>
        </div>
      );
    }

    // 准备ECharts图表数据
    const getPathChartOption = () => {
      // 提取经纬度用于折线图
      const latitudes = data.map((p) => p.latitude);
      const longitudes = data.map((p) => p.longitude);
      const windSpeeds = data.map((p) => p.max_wind_speed || p.wind_speed || 0);
      const timeLabels = data.map((p, index) => {
        const timestamp = p.timestamp || p.record_time || p.time;
        return timestamp
          ? new Date(timestamp).toLocaleString("zh-CN", {
              month: "2-digit",
              day: "2-digit",
              hour: "2-digit",
            })
          : `点${index + 1}`;
      });

      return {
        title: {
          text: "台风路径可视化",
          left: "center",
          textStyle: {
            color: "#1f2937",
            fontSize: 18,
            fontWeight: "bold",
          },
        },
        tooltip: {
          trigger: "axis",
          backgroundColor: "rgba(255, 255, 255, 0.95)",
          borderColor: "#667eea",
          borderWidth: 1,
          textStyle: {
            color: "#1f2937",
          },
          formatter: function (params) {
            const index = params[0].dataIndex;
            const point = data[index];
            const timestamp =
              point.timestamp || point.record_time || point.time;
            const windSpeed = point.max_wind_speed || point.wind_speed;
            const pressure = point.center_pressure || point.pressure;

            return `
              <div style="padding: 8px;">
                <strong style="color: #667eea;">路径点 ${
                  index + 1
                }</strong><br/>
                <strong>时间：</strong>${
                  timestamp
                    ? new Date(timestamp).toLocaleString("zh-CN")
                    : "暂无数据"
                }<br/>
                <strong>经度：</strong>${point.longitude?.toFixed(2)}°E<br/>
                <strong>纬度：</strong>${point.latitude?.toFixed(2)}°N<br/>
                <strong>风速：</strong>${windSpeed || "暂无数据"} m/s<br/>
                <strong>气压：</strong>${pressure || "暂无数据"} hPa<br/>
                <strong>强度：</strong>${point.intensity || "暂无数据"}
              </div>
            `;
          },
        },
        legend: {
          data: ["纬度", "经度", "风速"],
          top: 40,
          textStyle: {
            color: "#374151",
          },
        },
        grid: {
          left: "3%",
          right: "4%",
          bottom: "3%",
          top: 100,
          containLabel: true,
        },
        xAxis: {
          type: "category",
          data: timeLabels,
          boundaryGap: false,
          axisLabel: {
            rotate: 45,
            color: "#6b7280",
            fontSize: 11,
          },
          axisLine: {
            lineStyle: {
              color: "#e5e7eb",
            },
          },
        },
        yAxis: [
          {
            type: "value",
            name: "经纬度 (°)",
            position: "left",
            axisLabel: {
              color: "#6b7280",
              formatter: "{value}°",
            },
            axisLine: {
              lineStyle: {
                color: "#e5e7eb",
              },
            },
            splitLine: {
              lineStyle: {
                color: "#f3f4f6",
              },
            },
          },
          {
            type: "value",
            name: "风速 (m/s)",
            position: "right",
            axisLabel: {
              color: "#6b7280",
              formatter: "{value} m/s",
            },
            axisLine: {
              lineStyle: {
                color: "#e5e7eb",
              },
            },
            splitLine: {
              show: false,
            },
          },
        ],
        series: [
          {
            name: "纬度",
            type: "line",
            data: latitudes,
            smooth: true,
            symbol: "circle",
            symbolSize: 8,
            lineStyle: {
              color: "#667eea",
              width: 3,
            },
            itemStyle: {
              color: "#667eea",
            },
            areaStyle: {
              color: {
                type: "linear",
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: "rgba(102, 126, 234, 0.3)" },
                  { offset: 1, color: "rgba(102, 126, 234, 0.05)" },
                ],
              },
            },
          },
          {
            name: "经度",
            type: "line",
            data: longitudes,
            smooth: true,
            symbol: "circle",
            symbolSize: 8,
            lineStyle: {
              color: "#10b981",
              width: 3,
            },
            itemStyle: {
              color: "#10b981",
            },
            areaStyle: {
              color: {
                type: "linear",
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: "rgba(16, 185, 129, 0.3)" },
                  { offset: 1, color: "rgba(16, 185, 129, 0.05)" },
                ],
              },
            },
          },
          {
            name: "风速",
            type: "line",
            yAxisIndex: 1,
            data: windSpeeds,
            smooth: true,
            symbol: "diamond",
            symbolSize: 10,
            lineStyle: {
              color: "#FF9FE7",
              width: 2,
              type: "dashed",
            },
            itemStyle: {
              color: "#FF40CF",
            },
          },
        ],
      };
    };

    return (
      <div className="info-card" style={{ marginTop: "20px" }}>
        <h4>🗺️ 台风路径数据（共 {data.length} 个点）</h4>

        {/* ECharts可视化图表 */}
        <div
          style={{
            marginTop: "20px",
            marginBottom: "30px",
            background: "white",
            padding: "20px",
            borderRadius: "10px",
            boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)",
          }}
        >
          <ReactECharts
            option={getPathChartOption()}
            style={{ height: "500px", width: "100%" }}
            opts={{ renderer: "canvas" }}
          />
        </div>

        {/* 数据表格 */}
        <div
          style={{ overflowX: "auto", maxHeight: "600px", overflowY: "auto" }}
        >
          <table>
            <thead
              style={{
                position: "sticky",
                top: 0,
                background: "white",
                zIndex: 1,
              }}
            >
              <tr>
                <th>序号</th>
                <th>时间</th>
                <th>纬度</th>
                <th>经度</th>
                <th>风速(m/s)</th>
                <th>气压(hPa)</th>
                <th>移动速度(km/h)</th>
                <th>移动方向</th>
                <th>强度</th>
              </tr>
            </thead>
            <tbody>
              {data.map((point, index) => {
                // 修复字段名映射：参考index.html第2270、2275、2826-2827行
                const timestamp =
                  point.timestamp || point.record_time || point.time;
                const windSpeed = point.max_wind_speed || point.wind_speed;
                const pressure = point.center_pressure || point.pressure;
                const movingSpeed = point.moving_speed;
                const movingDirection = point.moving_direction;

                return (
                  <tr key={index}>
                    <td style={{ textAlign: "center" }}>{index + 1}</td>
                    <td>
                      {timestamp
                        ? new Date(timestamp).toLocaleString("zh-CN", {
                            year: "numeric",
                            month: "2-digit",
                            day: "2-digit",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "暂无数据"}
                    </td>
                    <td style={{ textAlign: "center" }}>
                      {point.latitude
                        ? `${point.latitude.toFixed(2)}°N`
                        : "暂无数据"}
                    </td>
                    <td style={{ textAlign: "center" }}>
                      {point.longitude
                        ? `${point.longitude.toFixed(2)}°E`
                        : "暂无数据"}
                    </td>
                    <td style={{ textAlign: "center" }}>
                      {windSpeed ? windSpeed : "暂无数据"}
                    </td>
                    <td style={{ textAlign: "center" }}>
                      {pressure ? pressure : "暂无数据"}
                    </td>
                    <td style={{ textAlign: "center" }}>
                      {movingSpeed ? movingSpeed : "暂无数据"}
                    </td>
                    <td style={{ textAlign: "center" }}>
                      {movingDirection || "暂无数据"}
                    </td>
                    <td>{point.intensity || "暂无数据"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p style={{ marginTop: "10px", color: "#6b7280", fontSize: "14px" }}>
          ✓ 显示全部 {data.length} 个路径点
        </p>
      </div>
    );
  };

  // 渲染爬虫数据
  const renderCrawlerData = () => {
    if (!crawlerData) return null;

    if (crawlerData.type === "status") {
      return (
        <div className="info-card" style={{ marginTop: "20px" }}>
          <h4>📊 爬虫状态</h4>
          <pre
            style={{
              background: "#f3f4f6",
              padding: "15px",
              borderRadius: "8px",
              overflow: "auto",
            }}
          >
            {JSON.stringify(crawlerData.data, null, 2)}
          </pre>
        </div>
      );
    } else if (crawlerData.type === "logs") {
      return (
        <div className="info-card" style={{ marginTop: "20px" }}>
          <h4>📝 爬虫日志</h4>
          <pre
            style={{
              background: "#f3f4f6",
              padding: "15px",
              borderRadius: "8px",
              overflow: "auto",
              maxHeight: "400px",
            }}
          >
            {JSON.stringify(crawlerData.data, null, 2)}
          </pre>
        </div>
      );
    }
  };

  // 渲染结果
  const renderResult = () => {
    if (!result) return null;

    if (result.type === "list") {
      return renderListResult(result.data);
    } else if (result.type === "detail") {
      return renderDetailResult(result.data);
    } else if (result.type === "search") {
      return renderSearchResult(result.data);
    } else if (result.type === "path") {
      return renderPathResult(result.data);
    }
  };

  return (
    <div>
      <h2 style={{ marginBottom: "20px" }}>🌊 台风数据查询</h2>

      {/* 左右分栏布局 - 参考index.html的grid-2 */}
      <div
        className="grid-2"
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "20px",
          marginBottom: "20px",
        }}
      >
        {/* 左侧：台风列表查询 */}
        <div>
          <h3>台风列表查询</h3>
          {renderListForm()}
        </div>

        {/* 右侧：台风详情查询 */}
        <div>
          <h3>台风详情查询</h3>
          {renderDetailForm()}
        </div>
      </div>

      {/* 爬虫状态与日志 - 参考index.html */}
      <div
        style={{
          marginTop: "30px",
          paddingTop: "20px",
          borderTop: "2px solid #e5e7eb",
        }}
      >
        <h3>📊 爬虫状态与日志</h3>
        <p style={{ color: "#666", margin: "10px 0" }}>
          查看定时爬取任务的运行状态和历史日志
        </p>
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            className="btn"
            onClick={handleGetCrawlerStatus}
            disabled={crawlerLoading}
          >
            📊 查看最近状态
          </button>
          <button
            className="btn"
            onClick={handleGetCrawlerLogs}
            disabled={crawlerLoading}
          >
            📝 查看完整日志
          </button>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="error-message" style={{ marginTop: "20px" }}>
          ❌ {error}
        </div>
      )}

      {/* 加载状态 */}
      {loading && <div className="loading">查询中...</div>}
      {crawlerLoading && <div className="loading">加载爬虫数据中...</div>}

      {/* 结果显示 - 每次只显示一个查询结果 */}
      {result && renderResult()}

      {/* 爬虫数据显示 */}
      {crawlerData && renderCrawlerData()}
    </div>
  );
}

export default TyphoonQuery;
