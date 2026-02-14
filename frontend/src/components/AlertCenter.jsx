/**
 * 预警中心组件
 */
import { useState, useEffect } from "react";
import { getActiveAlerts, getAlertHistory } from "../services/api";
import "../styles/AlertCenter.css";
import "../styles/common.css";

function AlertCenter() {
  const [alertFunction, setAlertFunction] = useState("active");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // 历史预警筛选表单
  const [historyForm, setHistoryForm] = useState({
    typhoonId: "",
    limit: 50,
  });

  // 加载活跃预警
  const loadActiveAlerts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getActiveAlerts();
      setResult({ type: "active", data: data });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 加载历史预警
  const loadAlertHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getAlertHistory(
        historyForm.typhoonId,
        null,
        historyForm.limit,
      );
      const alerts =
        data.items || data.alerts || (Array.isArray(data) ? data : []);
      setResult({ type: "history", data: { alerts } });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 当功能切换时自动加载数据
  useEffect(() => {
    if (alertFunction === "active") {
      loadActiveAlerts();
    }
  }, [alertFunction]);

  // 获取预警级别颜色
  const getAlertLevelColor = (level) => {
    const colors = {
      红色: "#ef4444",
      橙色: "#f97316",
      黄色: "#eab308",
      蓝色: "#3b82f6",
      red: "#ef4444",
      orange: "#f97316",
      yellow: "#eab308",
      blue: "#3b82f6",
    };
    return colors[level] || "#6b7280";
  };

  // 渲染活跃预警表单
  const renderActiveForm = () => (
    <div>
      <button className="btn" onClick={loadActiveAlerts} disabled={loading}>
        🔄 刷新台风公报
      </button>
    </div>
  );

  // 渲染历史预警表单
  const renderHistoryForm = () => (
    <div>
      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px" }}
      >
        <div className="form-group">
          <label>台风ID（可选）</label>
          <input
            type="text"
            placeholder="留空则查询所有台风"
            value={historyForm.typhoonId}
            onChange={(e) =>
              setHistoryForm({ ...historyForm, typhoonId: e.target.value })
            }
          />
        </div>
        <div className="form-group">
          <label>查询数量</label>
          <input
            type="number"
            placeholder="默认50条"
            value={historyForm.limit}
            onChange={(e) =>
              setHistoryForm({
                ...historyForm,
                limit: parseInt(e.target.value) || 50,
              })
            }
          />
        </div>
      </div>
      <button className="btn" onClick={loadAlertHistory} disabled={loading}>
        � 查询历史预警
      </button>
    </div>
  );

  // 渲染活跃预警结果 - 显示台风公报数据
  const renderActiveResult = (data) => {
    // 检查是否有台风公报
    if (!data.has_bulletin || !data.bulletin) {
      return (
        <div className="info-card">
          <p>✅ 当前没有活跃的台风公报</p>
        </div>
      );
    }

    const bulletin = data.bulletin;

    // 检查是否有实质性的台风信息（台风名称、编号、位置等）
    const hasActiveTyphoonInfo =
      bulletin.typhoon_name ||
      bulletin.typhoon_number ||
      bulletin.position ||
      bulletin.intensity;

    // 如果没有活跃台风信息，但有summary或description，显示简化版公报
    if (!hasActiveTyphoonInfo && (bulletin.summary || bulletin.description)) {
      return (
        <div className="info-card">
          <h4>📢 台风公报</h4>

          {/* 发布时间 */}
          {bulletin.release_time && (
            <div
              style={{
                background: "#f0f9ff",
                padding: "12px",
                borderRadius: "8px",
                marginBottom: "15px",
                borderLeft: "4px solid #3b82f6",
              }}
            >
              <p style={{ margin: "0", fontSize: "14px", color: "#1e40af" }}>
                <strong>发布时间：</strong>
                {bulletin.release_time}
              </p>
            </div>
          )}

          {/* 公报摘要 */}
          {bulletin.summary && (
            <div
              style={{
                padding: "15px",
                background: "#fef3c7",
                borderRadius: "8px",
                marginBottom: "12px",
                borderLeft: "4px solid #f59e0b",
              }}
            >
              <strong style={{ color: "#d97706", fontSize: "15px" }}>
                📋 公报摘要
              </strong>
              <div
                style={{
                  marginTop: "8px",
                  lineHeight: "1.8",
                  color: "#92400e",
                  fontSize: "14px",
                }}
              >
                {bulletin.summary}
              </div>
            </div>
          )}
          {/* 提示信息 */}
          <div
            style={{
              marginTop: "15px",
              padding: "10px",
              background: "#dcfce7",
              borderRadius: "6px",
              fontSize: "14px",
              color: "#166534",
            }}
          >
            ✅ 当前没有活跃的台风
          </div>
        </div>
      );
    }

    // 有活跃台风信息时，显示完整的台风公报
    return (
      <div className="info-card">
        <h4>🚨 台风公报</h4>

        {/* 台风基本信息 */}
        <div
          style={{
            background: "linear-gradient(135deg, #ea66c5ff 0%, #764ba2 100%)",
            color: "white",
            padding: "15px",
            borderRadius: "8px",
            marginBottom: "15px",
          }}
        >
          <h3 style={{ margin: "0 0 10px 0", fontSize: "18px" }}>
            {bulletin.typhoon_name || "台风信息"}
          </h3>
          {bulletin.typhoon_number && (
            <p style={{ margin: "5px 0", fontSize: "14px" }}>
              <strong>编号：</strong>
              {bulletin.typhoon_number}
            </p>
          )}
          {bulletin.release_time && (
            <p style={{ margin: "5px 0", fontSize: "14px" }}>
              <strong>发布时间：</strong>
              {bulletin.release_time}
            </p>
          )}
        </div>

        {/* 详细信息列表 */}
        <div style={{ display: "grid", gap: "12px" }}>
          {bulletin.time && (
            <div
              style={{
                padding: "10px",
                background: "#f9fafb",
                borderRadius: "6px",
              }}
            >
              <strong style={{ color: "#667eea" }}>观测时间：</strong>
              <span style={{ marginLeft: "10px" }}>{bulletin.time}</span>
            </div>
          )}

          {bulletin.position && (
            <div
              style={{
                padding: "10px",
                background: "#f9fafb",
                borderRadius: "6px",
              }}
            >
              <strong style={{ color: "#667eea" }}>中心位置：</strong>
              <span style={{ marginLeft: "10px" }}>{bulletin.position}</span>
            </div>
          )}

          {bulletin.intensity && (
            <div
              style={{
                padding: "10px",
                background: "#f9fafb",
                borderRadius: "6px",
              }}
            >
              <strong style={{ color: "#667eea" }}>强度等级：</strong>
              <span style={{ marginLeft: "10px" }}>{bulletin.intensity}</span>
            </div>
          )}

          {bulletin.max_wind && (
            <div
              style={{
                padding: "10px",
                background: "#f9fafb",
                borderRadius: "6px",
              }}
            >
              <strong style={{ color: "#667eea" }}>最大风力：</strong>
              <span style={{ marginLeft: "10px" }}>{bulletin.max_wind}</span>
            </div>
          )}

          {bulletin.center_pressure && (
            <div
              style={{
                padding: "10px",
                background: "#f9fafb",
                borderRadius: "6px",
              }}
            >
              <strong style={{ color: "#667eea" }}>中心气压：</strong>
              <span style={{ marginLeft: "10px" }}>
                {bulletin.center_pressure}
              </span>
            </div>
          )}

          {bulletin.reference_position && (
            <div
              style={{
                padding: "10px",
                background: "#f9fafb",
                borderRadius: "6px",
              }}
            >
              <strong style={{ color: "#667eea" }}>参考位置：</strong>
              <span style={{ marginLeft: "10px" }}>
                {bulletin.reference_position}
              </span>
            </div>
          )}

          {bulletin.wind_circle && (
            <div
              style={{
                padding: "10px",
                background: "#f9fafb",
                borderRadius: "6px",
              }}
            >
              <strong style={{ color: "#667eea" }}>风圈半径：</strong>
              <div style={{ marginTop: "5px", whiteSpace: "pre-line" }}>
                {bulletin.wind_circle}
              </div>
            </div>
          )}

          {bulletin.forecast && (
            <div
              style={{
                padding: "12px",
                background: "#fef3c7",
                borderRadius: "6px",
                borderLeft: "4px solid #f59e0b",
              }}
            >
              <strong style={{ color: "#d97706" }}>预报结论：</strong>
              <div style={{ marginTop: "5px", lineHeight: "1.6" }}>
                {bulletin.forecast}
              </div>
            </div>
          )}

          {/* 显示summary和description（如果有） */}
          {bulletin.summary && (
            <div
              style={{
                padding: "12px",
                background: "#f0f9ff",
                borderRadius: "6px",
                borderLeft: "4px solid #3b82f6",
              }}
            >
              <strong style={{ color: "#1e40af" }}>公报摘要：</strong>
              <div style={{ marginTop: "5px", lineHeight: "1.6" }}>
                {bulletin.summary}
              </div>
            </div>
          )}

          {bulletin.description &&
            bulletin.description !== bulletin.summary && (
              <div
                style={{
                  padding: "12px",
                  background: "#f9fafb",
                  borderRadius: "6px",
                  borderLeft: "4px solid #6b7280",
                }}
              >
                <strong style={{ color: "#374151" }}>详细描述：</strong>
                <div style={{ marginTop: "5px", lineHeight: "1.6" }}>
                  {bulletin.description}
                </div>
              </div>
            )}
        </div>
      </div>
    );
  };

  // 渲染历史预警结果
  const renderHistoryResult = (data) => {
    const items = data.alerts || [];
    const total = data.total || items.length;

    if (items.length === 0) {
      return (
        <div className="info-card">
          <p>暂无历史预警记录</p>
        </div>
      );
    }

    return (
      <div className="info-card">
        <h4>📜 历史预警记录 (共{total}条)</h4>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "12px",
          }}
        >
          <thead>
            <tr style={{ background: "#f3f4f6" }}>
              <th style={{ padding: "6px", border: "1px solid #ddd" }}>台风</th>
              <th style={{ padding: "6px", border: "1px solid #ddd" }}>
                预警级别
              </th>
              <th style={{ padding: "6px", border: "1px solid #ddd" }}>
                预警原因
              </th>
              <th style={{ padding: "6px", border: "1px solid #ddd" }}>
                预警时间
              </th>
              <th style={{ padding: "6px", border: "1px solid #ddd" }}>状态</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, index) => {
              const alertLevel = item.alert_level || item.level;
              const levelColor = getAlertLevelColor(alertLevel);

              return (
                <tr key={index}>
                  <td style={{ padding: "6px", border: "1px solid #ddd" }}>
                    {item.typhoon_name}
                  </td>
                  <td
                    style={{
                      padding: "6px",
                      border: "1px solid #ddd",
                      textAlign: "center",
                      color: levelColor,
                      fontWeight: "bold",
                    }}
                  >
                    {alertLevel}
                  </td>
                  <td style={{ padding: "6px", border: "1px solid #ddd" }}>
                    {item.alert_reason || item.message}
                  </td>
                  <td
                    style={{
                      padding: "6px",
                      border: "1px solid #ddd",
                      textAlign: "center",
                    }}
                  >
                    {new Date(item.alert_time).toLocaleString("zh-CN")}
                  </td>
                  <td
                    style={{
                      padding: "6px",
                      border: "1px solid #ddd",
                      textAlign: "center",
                    }}
                  >
                    {item.status === "resolved" ? "已解除" : "活跃"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div>
      <h2>🚨 预警中心</h2>

      {/* 功能选择 */}
      <div className="form-group">
        <label>功能选择</label>
        <select
          value={alertFunction}
          onChange={(e) => setAlertFunction(e.target.value)}
        >
          <option value="active">台风公报</option>
          <option value="history">历史预警</option>
        </select>
      </div>

      {/* 根据功能渲染不同表单 */}
      {alertFunction === "active" && renderActiveForm()}
      {alertFunction === "history" && renderHistoryForm()}

      {/* 错误提示 */}
      {error && (
        <div className="error-message" style={{ marginTop: "20px" }}>
          ❌ {error}
        </div>
      )}

      {/* 加载状态 */}
      {loading && <div className="loading">处理中</div>}

      {/* 结果显示 */}
      {result && (
        <div style={{ marginTop: "20px" }}>
          {result.type === "active" && renderActiveResult(result.data)}
          {result.type === "history" && renderHistoryResult(result.data)}
        </div>
      )}
    </div>
  );
}

export default AlertCenter;
