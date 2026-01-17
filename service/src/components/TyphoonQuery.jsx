/**
 * 台风数据查询组件
 */
import React, { useState } from "react";
import {
  getTyphoonList,
  getTyphoonById,
  searchTyphoons,
  getCrawlerStatus,
  getCrawlerLogs,
  getTyphoonPath,
} from "../services/api";
import "../styles/TyphoonQuery.css";
import "../styles/common.css";

function TyphoonQuery() {
  const [queryType, setQueryType] = useState("list");
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
          (t) => t.year === parseInt(listForm.year)
        );
      }
      if (listForm.status !== "") {
        filteredData = filteredData.filter(
          (t) => t.status === parseInt(listForm.status)
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
  const handleDetailQuery = async () => {
    if (!detailForm.typhoonId) {
      alert("请输入台风ID");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // 同时获取台风详情和路径数据
      const [detailData, pathData] = await Promise.all([
        getTyphoonById(detailForm.typhoonId),
        getTyphoonPath(detailForm.typhoonId).catch(() => ({ items: [] })),
      ]);

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
              timestamps[timestamps.length - 1]
            ).toISOString();
          }
        }
      }

      setResult({ type: "detail", data: detailData });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 处理台风路径查询
  const handlePathQuery = async () => {
    if (!detailForm.typhoonId) {
      alert("请输入台风ID");
      return;
    }

    try {
      setLoading(true);
      setError(null);
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

  // 渲染台风详情表单
  const renderDetailForm = () => (
    <div>
      <div className="form-group">
        <label>台风ID</label>
        <input
          type="text"
          placeholder="例如: 2501"
          value={detailForm.typhoonId}
          onChange={(e) =>
            setDetailForm({ ...detailForm, typhoonId: e.target.value })
          }
        />
      </div>
      <div style={{ display: "flex", gap: "10px" }}>
        <button className="btn" onClick={handleDetailQuery} disabled={loading}>
          🔍 查询台风详情
        </button>
        <button className="btn" onClick={handlePathQuery} disabled={loading}>
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

  // 渲染台风详情结果
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
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "15px",
          }}
        >
          <div>
            <p>
              <strong>台风ID:</strong> {data.typhoon_id}
            </p>
            <p>
              <strong>中文名:</strong> {data.typhoon_name_cn || "暂无数据"}
            </p>
            <p>
              <strong>英文名:</strong> {data.typhoon_name || "暂无数据"}
            </p>
            <p>
              <strong>年份:</strong> {data.year}
            </p>
            <p>
              <strong>状态:</strong> {data.status === 1 ? "活跃" : "已停止"}
            </p>
          </div>
          <div>
            <p>
              <strong>最大风速:</strong>{" "}
              {data.max_wind_speed ? `${data.max_wind_speed} m/s` : "暂无数据"}
            </p>
            <p>
              <strong>最低气压:</strong>{" "}
              {data.min_pressure ? `${data.min_pressure} hPa` : "暂无数据"}
            </p>
            <p>
              <strong>最大强度:</strong> {data.max_intensity || "暂无数据"}
            </p>
            <p>
              <strong>起始时间:</strong>{" "}
              {data.start_time
                ? new Date(data.start_time).toLocaleString("zh-CN")
                : data.created_at
                ? new Date(data.created_at).toLocaleString("zh-CN")
                : "暂无数据"}
            </p>
            <p>
              <strong>结束时间:</strong>{" "}
              {data.end_time
                ? new Date(data.end_time).toLocaleString("zh-CN")
                : data.updated_at
                ? new Date(data.updated_at).toLocaleString("zh-CN")
                : "暂无数据"}
            </p>
          </div>
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

    return (
      <div className="info-card" style={{ marginTop: "20px" }}>
        <h4>🗺️ 台风路径数据（共 {data.length} 个点）</h4>
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
          ✓ 显示全部 {data.length} 个路径点（支持滚动查看）
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
