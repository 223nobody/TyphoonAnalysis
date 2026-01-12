/**
 * 预警中心组件
 */
import React, { useState, useEffect } from "react";
import {
  getActiveAlerts,
  getAlertHistory,
  getAlertRules,
  createAlertRule,
} from "../services/api";

function AlertCenter() {
  const [alertFunction, setAlertFunction] = useState("active");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // 历史预警筛选表单
  const [historyForm, setHistoryForm] = useState({
    typhoonId: "",
    level: "",
    limit: 20, // 添加limit参数，默认20
  });

  // 预警规则表单
  const [ruleForm, setRuleForm] = useState({
    ruleName: "",
    windSpeedThreshold: "",
    pressureThreshold: "",
    alertLevel: "yellow",
  });

  // 加载活跃预警
  const loadActiveAlerts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getActiveAlerts();
      // 修复：处理不同的数据格式
      const alerts =
        data.items || data.alerts || (Array.isArray(data) ? data : []);
      setResult({ type: "active", data: { alerts } });
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
        historyForm.level,
        historyForm.limit // 添加limit参数
      );
      // 修复：处理不同的数据格式
      const alerts =
        data.items || data.alerts || (Array.isArray(data) ? data : []);
      setResult({ type: "history", data: { alerts } });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 加载预警规则
  const loadAlertRules = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getAlertRules();
      // 修复：处理不同的数据格式
      const rules =
        data.items || data.rules || (Array.isArray(data) ? data : []);
      setResult({ type: "rules", data: { rules } });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 创建预警规则
  const handleCreateRule = async () => {
    if (!ruleForm.ruleName) {
      alert("请输入规则名称");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await createAlertRule({
        rule_name: ruleForm.ruleName,
        wind_speed_threshold: parseFloat(ruleForm.windSpeedThreshold) || null,
        pressure_threshold: parseFloat(ruleForm.pressureThreshold) || null,
        alert_level: ruleForm.alertLevel,
      });
      alert("预警规则创建成功！");
      // 重新加载规则列表
      await loadAlertRules();
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
    } else if (alertFunction === "rules") {
      loadAlertRules();
    }
  }, [alertFunction]);

  // 获取预警级别颜色 - 参考index.html，支持中文和英文
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

  // 获取预警级别中文名 - 参考index.html
  const getAlertLevelName = (level) => {
    const names = {
      红色: "红色预警",
      橙色: "橙色预警",
      黄色: "黄色预警",
      蓝色: "蓝色预警",
      red: "红色预警",
      orange: "橙色预警",
      yellow: "黄色预警",
      blue: "蓝色预警",
    };
    return names[level] || level;
  };

  // 渲染活跃预警表单
  const renderActiveForm = () => (
    <div>
      <button className="btn" onClick={loadActiveAlerts} disabled={loading}>
        🔄 刷新活跃预警
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
          <label>预警级别（可选）</label>
          <select
            value={historyForm.level}
            onChange={(e) =>
              setHistoryForm({ ...historyForm, level: e.target.value })
            }
          >
            <option value="">全部级别</option>
            <option value="红色">红色预警</option>
            <option value="橙色">橙色预警</option>
            <option value="黄色">黄色预警</option>
            <option value="蓝色">蓝色预警</option>
          </select>
        </div>
      </div>
      <div className="form-group">
        <label>查询数量</label>
        <input
          type="number"
          placeholder="默认20条"
          value={historyForm.limit}
          min="1"
          max="100"
          onChange={(e) =>
            setHistoryForm({
              ...historyForm,
              limit: parseInt(e.target.value) || 20,
            })
          }
        />
      </div>
      <button className="btn" onClick={loadAlertHistory} disabled={loading}>
        🔍 查询历史预警
      </button>
    </div>
  );

  // 渲染预警规则表单
  const renderRulesForm = () => (
    <div>
      <div className="info-card">
        <h4>➕ 创建新规则</h4>
        <div className="form-group">
          <label>规则名称</label>
          <input
            type="text"
            placeholder="例如: 强台风预警规则"
            value={ruleForm.ruleName}
            onChange={(e) =>
              setRuleForm({ ...ruleForm, ruleName: e.target.value })
            }
          />
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "15px",
          }}
        >
          <div className="form-group">
            <label>风速阈值 (m/s)</label>
            <input
              type="number"
              placeholder="例如: 50"
              value={ruleForm.windSpeedThreshold}
              onChange={(e) =>
                setRuleForm({ ...ruleForm, windSpeedThreshold: e.target.value })
              }
            />
          </div>
          <div className="form-group">
            <label>气压阈值 (hPa)</label>
            <input
              type="number"
              placeholder="例如: 950"
              value={ruleForm.pressureThreshold}
              onChange={(e) =>
                setRuleForm({ ...ruleForm, pressureThreshold: e.target.value })
              }
            />
          </div>
        </div>
        <div className="form-group">
          <label>预警级别</label>
          <select
            value={ruleForm.alertLevel}
            onChange={(e) =>
              setRuleForm({ ...ruleForm, alertLevel: e.target.value })
            }
          >
            <option value="blue">蓝色预警</option>
            <option value="yellow">黄色预警</option>
            <option value="orange">橙色预警</option>
            <option value="red">红色预警</option>
          </select>
        </div>
        <button className="btn" onClick={handleCreateRule} disabled={loading}>
          ✅ 创建规则
        </button>
      </div>
      <div
        className="info-card"
        style={{
          marginBottom: "20px",
          height: "200px",
          minHeight: "200px",
        }}
      >
        <h4>📋 现有规则</h4>
        <button className="btn" onClick={loadAlertRules} disabled={loading}>
          🔄 刷新规则列表
        </button>
      </div>
    </div>
  );

  // 渲染活跃预警结果 - 参考index.html的displayAlertResult函数
  const renderActiveResult = (data) => {
    const alerts = data.alerts || [];
    const count = data.count || alerts.length;

    if (alerts.length === 0) {
      return (
        <div className="info-card">
          <p>✅ 当前没有活跃预警</p>
        </div>
      );
    }

    return (
      <div className="info-card">
        <h4>🚨 当前活跃预警 ({count}个)</h4>
        {alerts.map((alert, index) => {
          // 支持alert_level和level两种字段名
          const alertLevel = alert.alert_level || alert.level;
          const levelColor = getAlertLevelColor(alertLevel);

          return (
            <div
              key={index}
              style={{
                borderLeft: `4px solid ${levelColor}`,
                padding: "10px",
                margin: "10px 0",
                background: "#f9fafb",
              }}
            >
              <h5 style={{ margin: "0 0 8px 0", color: levelColor }}>
                {alertLevel}预警
              </h5>
              <p>
                <strong>台风:</strong>{" "}
                {alert.typhoon_name_cn || alert.typhoon_name} (
                {alert.typhoon_id})
              </p>
              <p>
                <strong>原因:</strong> {alert.alert_reason || alert.message}
              </p>
              {alert.current_intensity && (
                <p>
                  <strong>当前强度:</strong> {alert.current_intensity}
                </p>
              )}
              {alert.current_wind_speed && (
                <p>
                  <strong>最大风速:</strong> {alert.current_wind_speed} m/s
                </p>
              )}
              {alert.current_pressure && (
                <p>
                  <strong>中心气压:</strong> {alert.current_pressure} hPa
                </p>
              )}
              {alert.latest_position && (
                <p>
                  <strong>最新位置:</strong> {alert.latest_position.latitude}°N,{" "}
                  {alert.latest_position.longitude}°E
                </p>
              )}
              <p style={{ color: "#6b7280", fontSize: "12px" }}>
                <strong>预警时间:</strong>{" "}
                {new Date(alert.alert_time).toLocaleString("zh-CN")}
              </p>
            </div>
          );
        })}
      </div>
    );
  };

  // 渲染历史预警结果 - 参考index.html的displayAlertResult函数
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
              // 支持alert_level和level两种字段名
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

  // 渲染预警规则结果 - 参考index.html的displayAlertResult函数
  const renderRulesResult = (data) => {
    const rules = data.rules || [];
    const count = data.count || rules.length;

    if (rules.length === 0) {
      return (
        <div className="info-card">
          <p>暂无预警规则</p>
        </div>
      );
    }

    return (
      <div className="info-card">
        <h4>📋 预警规则列表 (共{count}条)</h4>
        {rules.map((rule, index) => (
          <div
            key={index}
            style={{
              border: "1px solid #e5e7eb",
              padding: "12px",
              margin: "10px 0",
              borderRadius: "6px",
              background: rule.enabled ? "#f0fdf4" : "#f9fafb",
            }}
          >
            <h5 style={{ margin: "0 0 8px 0" }}>
              {rule.rule_name} {rule.enabled ? "✅" : "❌"}
            </h5>
            <p style={{ fontSize: "12px", color: "#6b7280" }}>
              <strong>条件:</strong>
            </p>
            <ul
              style={{ margin: "5px 0", paddingLeft: "20px", fontSize: "12px" }}
            >
              {rule.conditions?.intensity && (
                <li>强度: {rule.conditions.intensity.join(", ")}</li>
              )}
              {rule.conditions?.wind_speed_min && (
                <li>最小风速: {rule.conditions.wind_speed_min} m/s</li>
              )}
              {rule.conditions?.pressure_max && (
                <li>最大气压: {rule.conditions.pressure_max} hPa</li>
              )}
              {rule.conditions?.distance_to_land_km && (
                <li>距离陆地: {rule.conditions.distance_to_land_km} km</li>
              )}
            </ul>
            {rule.notification_channels && (
              <p style={{ fontSize: "11px", color: "#9ca3af" }}>
                通知渠道: {rule.notification_channels.join(", ")}
              </p>
            )}
          </div>
        ))}
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
          <option value="active">活跃预警</option>
          <option value="history">历史预警</option>
          <option value="rules">预警规则</option>
        </select>
      </div>

      {/* 根据功能渲染不同表单 */}
      {alertFunction === "active" && renderActiveForm()}
      {alertFunction === "history" && renderHistoryForm()}
      {alertFunction === "rules" && renderRulesForm()}

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
          {result.type === "rules" && renderRulesResult(result.data)}
        </div>
      )}
    </div>
  );
}

export default AlertCenter;
