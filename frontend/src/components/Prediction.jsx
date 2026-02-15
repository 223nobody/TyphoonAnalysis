/**
 * 智能预测组件 - 集成LSTM深度学习模型
 * 支持：路径预测、强度预测、任意起点预测、滚动预测、虚拟观测点预测
 */
import React, { useState } from "react";
import {
  predictPath,
  predictFromArbitraryStart,
  rollingPrediction,
  predictWithVirtualObservations,
} from "../services/api";
import "../styles/ImageAnalysis.css";
import "../styles/common.css";

function Prediction() {
  const [predictionType, setPredictionType] = useState("path");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // 路径预测表单
  const [pathForm, setPathForm] = useState({
    typhoonId: "",
    hours: 48,
    useEnsemble: false,
  });

  // 任意起点预测表单
  const [arbitraryForm, setArbitraryForm] = useState({
    typhoonId: "",
    startTime: "",
    startLatitude: "",
    startLongitude: "",
    startPressure: "",
    startWindSpeed: "",
    hours: 48,
  });

  // 滚动预测表单
  const [rollingForm, setRollingForm] = useState({
    typhoonId: "",
    initialHours: 48,
    updateInterval: 6,
    maxIterations: 5,
    confidenceThreshold: 0.6,
  });

  // 虚拟观测点预测表单
  const [virtualForm, setVirtualForm] = useState({
    typhoonId: "",
    virtualObservations: [{ timestamp: "", latitude: "", longitude: "" }],
    hours: 48,
  });

  // 获取强度等级
  const getIntensityLevel = (windSpeed, pressure) => {
    if (!windSpeed) return "未知";
    if (windSpeed >= 51) return "超强台风";
    if (windSpeed >= 41) return "强台风";
    if (windSpeed >= 32) return "台风";
    if (windSpeed >= 24) return "强热带风暴";
    if (windSpeed >= 17) return "热带风暴";
    return "热带低压";
  };

  // 获取置信度颜色
  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.7) return "#22c55e";
    if (confidence >= 0.5) return "#eab308";
    return "#ef4444";
  };

  // 验证台风ID格式
  const validateTyphoonId = (id) => {
    if (!id) return false;
    const cleanId = id.trim();
    return /^\d{4}$/.test(cleanId) || /^\d{6}$/.test(cleanId);
  };

  // 处理路径预测
  const handlePathPrediction = async () => {
    if (!validateTyphoonId(pathForm.typhoonId)) {
      setError("请输入有效的台风编号（4位或6位数字）");
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const response = await predictPath(
        pathForm.typhoonId,
        parseInt(pathForm.hours),
        pathForm.useEnsemble,
      );
      setResult({ type: "path", data: response });
    } catch (err) {
      setError(err.message || "路径预测失败");
    } finally {
      setLoading(false);
    }
  };

  // 处理任意起点预测
  const handleArbitraryPrediction = async () => {
    if (!validateTyphoonId(arbitraryForm.typhoonId)) {
      setError("请输入有效的台风编号（4位或6位数字）");
      return;
    }
    if (!arbitraryForm.startTime) {
      setError("请输入起点时间");
      return;
    }
    if (!arbitraryForm.startLatitude || !arbitraryForm.startLongitude) {
      setError("请输入起点经纬度");
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const response = await predictFromArbitraryStart(
        arbitraryForm.typhoonId,
        arbitraryForm.startTime,
        parseFloat(arbitraryForm.startLatitude),
        parseFloat(arbitraryForm.startLongitude),
        arbitraryForm.startPressure
          ? parseFloat(arbitraryForm.startPressure)
          : null,
        arbitraryForm.startWindSpeed
          ? parseFloat(arbitraryForm.startWindSpeed)
          : null,
        parseInt(arbitraryForm.hours),
      );
      setResult({ type: "arbitrary", data: response });
    } catch (err) {
      setError(err.message || "任意起点预测失败");
    } finally {
      setLoading(false);
    }
  };

  // 处理滚动预测
  const handleRollingPrediction = async () => {
    if (!validateTyphoonId(rollingForm.typhoonId)) {
      setError("请输入有效的台风编号（4位或6位数字）");
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const response = await rollingPrediction(
        rollingForm.typhoonId,
        parseInt(rollingForm.initialHours),
        parseInt(rollingForm.updateInterval),
        parseInt(rollingForm.maxIterations),
        parseFloat(rollingForm.confidenceThreshold),
      );
      setResult({ type: "rolling", data: response });
    } catch (err) {
      setError(err.message || "滚动预测失败");
    } finally {
      setLoading(false);
    }
  };

  // 处理虚拟观测点预测
  const handleVirtualPrediction = async () => {
    if (!validateTyphoonId(virtualForm.typhoonId)) {
      setError("请输入有效的台风编号（4位或6位数字）");
      return;
    }
    // 过滤掉空的观测点
    const validObservations = virtualForm.virtualObservations.filter(
      (obs) => obs.timestamp && obs.latitude && obs.longitude,
    );
    if (validObservations.length === 0) {
      setError("请至少输入一个完整的虚拟观测点");
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const response = await predictWithVirtualObservations(
        virtualForm.typhoonId,
        validObservations,
        parseInt(virtualForm.hours),
      );
      setResult({ type: "virtual", data: response });
    } catch (err) {
      setError(err.message || "虚拟观测点预测失败");
    } finally {
      setLoading(false);
    }
  };

  // 添加虚拟观测点
  const addVirtualObservation = () => {
    setVirtualForm({
      ...virtualForm,
      virtualObservations: [
        ...virtualForm.virtualObservations,
        { timestamp: "", latitude: "", longitude: "" },
      ],
    });
  };

  // 删除虚拟观测点
  const removeVirtualObservation = (index) => {
    const newObservations = virtualForm.virtualObservations.filter(
      (_, i) => i !== index,
    );
    setVirtualForm({ ...virtualForm, virtualObservations: newObservations });
  };

  // 更新虚拟观测点
  const updateVirtualObservation = (index, field, value) => {
    const newObservations = [...virtualForm.virtualObservations];
    newObservations[index][field] = value;
    setVirtualForm({ ...virtualForm, virtualObservations: newObservations });
  };

  // 渲染预测结果概览
  const renderPredictionOverview = (data) => {
    if (!data || data.length === 0) return null;
    const firstPrediction = data[0];
    const inputData = firstPrediction.input_data || {};

    return (
      <div
        className="info-card"
        style={{ marginBottom: "15px", background: "#f0f9ff" }}
      >
        <h4>📊 预测概览</h4>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1fr",
            gap: "10px",
          }}
        >
          <div>
            <p style={{ margin: "5px 0", fontSize: "13px", color: "#666" }}>
              台风编号
            </p>
            <p style={{ margin: 0, fontWeight: "bold" }}>
              {firstPrediction.typhoon_id}
            </p>
          </div>
          <div>
            <p style={{ margin: "5px 0", fontSize: "13px", color: "#666" }}>
              台风名称
            </p>
            <p style={{ margin: 0, fontWeight: "bold" }}>
              {firstPrediction.typhoon_name || "N/A"}
            </p>
          </div>
          <div>
            <p style={{ margin: "5px 0", fontSize: "13px", color: "#666" }}>
              预报时效
            </p>
            <p style={{ margin: 0, fontWeight: "bold" }}>
              {firstPrediction.forecast_hours} 小时
            </p>
          </div>
          <div>
            <p style={{ margin: "5px 0", fontSize: "13px", color: "#666" }}>
              预测模型
            </p>
            <p style={{ margin: 0, fontWeight: "bold" }}>
              {firstPrediction.prediction_model}
            </p>
          </div>
          <div>
            <p style={{ margin: "5px 0", fontSize: "13px", color: "#666" }}>
              历史数据点
            </p>
            <p style={{ margin: 0, fontWeight: "bold" }}>
              {inputData.history_count || "N/A"}
            </p>
          </div>
          <div>
            <p style={{ margin: "5px 0", fontSize: "13px", color: "#666" }}>
              是否降级
            </p>
            <p
              style={{
                margin: 0,
                fontWeight: "bold",
                color: inputData.is_fallback ? "#ef4444" : "#22c55e",
              }}
            >
              {inputData.is_fallback ? "是" : "否"}
            </p>
          </div>
        </div>
      </div>
    );
  };

  // 渲染预测结果表格
  const renderPredictionTable = (data, showIntensity = false) => {
    if (!data || data.length === 0) {
      return (
        <div className="info-card">
          <p>暂无预测数据</p>
        </div>
      );
    }

    return (
      <div>
        {renderPredictionOverview(data)}
        <div className="info-card">
          <h4>🎯 预测结果</h4>
          <p>
            <strong>预测点数:</strong> {data.length}
          </p>

          <table style={{ marginTop: "15px", width: "100%" }}>
            <thead>
              <tr>
                <th>预报时间</th>
                <th>纬度</th>
                <th>经度</th>
                {showIntensity && <th>气压</th>}
                {showIntensity && <th>风速</th>}
                {showIntensity && <th>强度等级</th>}
                <th>置信度</th>
              </tr>
            </thead>
            <tbody>
              {data.map((pred, index) => (
                <tr key={index}>
                  <td>
                    {new Date(pred.forecast_time).toLocaleString("zh-CN")}
                  </td>
                  <td style={{ textAlign: "center" }}>
                    {pred.predicted_latitude?.toFixed(2) || "N/A"}°
                  </td>
                  <td style={{ textAlign: "center" }}>
                    {pred.predicted_longitude?.toFixed(2) || "N/A"}°
                  </td>
                  {showIntensity && (
                    <td style={{ textAlign: "center" }}>
                      {pred.predicted_pressure?.toFixed(0) || "N/A"} hPa
                    </td>
                  )}
                  {showIntensity && (
                    <td style={{ textAlign: "center" }}>
                      {pred.predicted_wind_speed?.toFixed(1) || "N/A"} m/s
                    </td>
                  )}
                  {showIntensity && (
                    <td style={{ textAlign: "center" }}>
                      <span
                        style={{
                          padding: "2px 8px",
                          borderRadius: "4px",
                          background:
                            pred.predicted_wind_speed >= 32
                              ? "#fee2e2"
                              : "#fef3c7",
                          color:
                            pred.predicted_wind_speed >= 32
                              ? "#dc2626"
                              : "#d97706",
                          fontWeight: "bold",
                          fontSize: "12px",
                        }}
                      >
                        {getIntensityLevel(
                          pred.predicted_wind_speed,
                          pred.predicted_pressure,
                        )}
                      </span>
                    </td>
                  )}
                  <td style={{ textAlign: "center" }}>
                    <span
                      style={{
                        color: getConfidenceColor(pred.confidence),
                        fontWeight: "bold",
                      }}
                    >
                      {(pred.confidence * 100).toFixed(1)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // 渲染滚动预测结果
  const renderRollingResult = (data) => {
    if (!data || data.length === 0) {
      return (
        <div className="info-card">
          <p>暂无预测数据</p>
        </div>
      );
    }

    return (
      <div>
        <div
          className="info-card"
          style={{ marginBottom: "15px", background: "#f0f9ff" }}
        >
          <h4>📊 滚动预测概览</h4>
          <p>
            <strong>总迭代次数:</strong> {data.length}
          </p>
        </div>
        {data.map((iteration, idx) => (
          <div key={idx} className="info-card" style={{ marginBottom: "15px" }}>
            <h4>🔄 第 {idx + 1} 次迭代</h4>
            {renderPredictionTable(iteration, true)}
          </div>
        ))}
      </div>
    );
  };

  // 渲染路径预测表单
  const renderPathForm = () => (
    <div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 1fr 1fr",
          gap: "15px",
        }}
      >
        <div className="form-group">
          <label>台风编号</label>
          <input
            type="text"
            placeholder="例如: 2601 或 202601"
            value={pathForm.typhoonId}
            onChange={(e) =>
              setPathForm({ ...pathForm, typhoonId: e.target.value })
            }
          />
        </div>
        <div className="form-group">
          <label>预报时效（小时）</label>
          <select
            value={pathForm.hours}
            onChange={(e) =>
              setPathForm({ ...pathForm, hours: e.target.value })
            }
          >
            <option value={12}>12小时</option>
            <option value={24}>24小时</option>
            <option value={48}>48小时</option>
            <option value={72}>72小时</option>
            <option value={120}>120小时</option>
          </select>
        </div>
        <div className="form-group">
          <label>集合预测</label>
          <select
            value={pathForm.useEnsemble}
            onChange={(e) =>
              setPathForm({
                ...pathForm,
                useEnsemble: e.target.value === "true",
              })
            }
          >
            <option value="false">否</option>
            <option value="true">是</option>
          </select>
        </div>
      </div>
      <button className="btn" onClick={handlePathPrediction} disabled={loading}>
        🎯 开始路径预测
      </button>
      <div className="info-card" style={{ marginTop: "15px" }}>
        <p style={{ margin: 0, fontSize: "13px", color: "#1e40af" }}>
          💡 <strong>说明：</strong>
          基于LSTM深度学习模型，预测未来台风移动轨迹。支持4位(如2601)或6位(如202601)台风编号。
        </p>
      </div>
    </div>
  );

  // 渲染任意起点预测表单
  const renderArbitraryForm = () => (
    <div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: "15px",
        }}
      >
        <div className="form-group">
          <label>台风编号</label>
          <input
            type="text"
            placeholder="例如: 2601 或 202601"
            value={arbitraryForm.typhoonId}
            onChange={(e) =>
              setArbitraryForm({ ...arbitraryForm, typhoonId: e.target.value })
            }
          />
        </div>
        <div className="form-group">
          <label>起点时间</label>
          <input
            type="datetime-local"
            value={arbitraryForm.startTime}
            onChange={(e) =>
              setArbitraryForm({ ...arbitraryForm, startTime: e.target.value })
            }
          />
        </div>
        <div className="form-group">
          <label>预报时效（小时）</label>
          <select
            value={arbitraryForm.hours}
            onChange={(e) =>
              setArbitraryForm({ ...arbitraryForm, hours: e.target.value })
            }
          >
            <option value={12}>12小时</option>
            <option value={24}>24小时</option>
            <option value={48}>48小时</option>
            <option value={72}>72小时</option>
            <option value={120}>120小时</option>
          </select>
        </div>
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr 1fr",
          gap: "15px",
          marginTop: "15px",
        }}
      >
        <div className="form-group">
          <label>起点纬度</label>
          <input
            type="number"
            step="0.01"
            placeholder="例如: 20.5"
            value={arbitraryForm.startLatitude}
            onChange={(e) =>
              setArbitraryForm({
                ...arbitraryForm,
                startLatitude: e.target.value,
              })
            }
          />
        </div>
        <div className="form-group">
          <label>起点经度</label>
          <input
            type="number"
            step="0.01"
            placeholder="例如: 125.8"
            value={arbitraryForm.startLongitude}
            onChange={(e) =>
              setArbitraryForm({
                ...arbitraryForm,
                startLongitude: e.target.value,
              })
            }
          />
        </div>
        <div className="form-group">
          <label>起点气压（可选）</label>
          <input
            type="number"
            placeholder="例如: 980"
            value={arbitraryForm.startPressure}
            onChange={(e) =>
              setArbitraryForm({
                ...arbitraryForm,
                startPressure: e.target.value,
              })
            }
          />
        </div>
        <div className="form-group">
          <label>起点风速（可选）</label>
          <input
            type="number"
            step="0.1"
            placeholder="例如: 30"
            value={arbitraryForm.startWindSpeed}
            onChange={(e) =>
              setArbitraryForm({
                ...arbitraryForm,
                startWindSpeed: e.target.value,
              })
            }
          />
        </div>
      </div>
      <button
        className="btn"
        onClick={handleArbitraryPrediction}
        disabled={loading}
        style={{ marginTop: "15px" }}
      >
        🎯 开始任意起点预测
      </button>
      <div className="info-card" style={{ marginTop: "15px" }}>
        <p style={{ margin: 0, fontSize: "13px", color: "#1e40af" }}>
          💡 <strong>说明：</strong>
          从指定的起点时间和位置开始预测。用于假设情景分析或多机构预报对比。
        </p>
      </div>
    </div>
  );

  // 渲染滚动预测表单
  const renderRollingForm = () => (
    <div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 1fr 1fr 1fr",
          gap: "15px",
        }}
      >
        <div className="form-group">
          <label>台风编号</label>
          <input
            type="text"
            placeholder="例如: 2601 或 202601"
            value={rollingForm.typhoonId}
            onChange={(e) =>
              setRollingForm({ ...rollingForm, typhoonId: e.target.value })
            }
          />
        </div>
        <div className="form-group">
          <label>初始预报时效（小时）</label>
          <select
            value={rollingForm.initialHours}
            onChange={(e) =>
              setRollingForm({ ...rollingForm, initialHours: e.target.value })
            }
          >
            <option value={12}>12小时</option>
            <option value={24}>24小时</option>
            <option value={48}>48小时</option>
            <option value={72}>72小时</option>
          </select>
        </div>
        <div className="form-group">
          <label>更新间隔（小时）</label>
          <select
            value={rollingForm.updateInterval}
            onChange={(e) =>
              setRollingForm({
                ...rollingForm,
                updateInterval: e.target.value,
              })
            }
          >
            <option value={3}>3小时</option>
            <option value={6}>6小时</option>
            <option value={12}>12小时</option>
          </select>
        </div>
        <div className="form-group">
          <label>最大迭代次数</label>
          <input
            type="number"
            min="1"
            max="20"
            value={rollingForm.maxIterations}
            onChange={(e) =>
              setRollingForm({
                ...rollingForm,
                maxIterations: e.target.value,
              })
            }
          />
        </div>
      </div>
      <div style={{ marginTop: "15px" }}>
        <div className="form-group" style={{ maxWidth: "300px" }}>
          <label>置信度阈值（低于此值停止滚动）</label>
          <input
            type="number"
            step="0.1"
            min="0"
            max="1"
            value={rollingForm.confidenceThreshold}
            onChange={(e) =>
              setRollingForm({
                ...rollingForm,
                confidenceThreshold: e.target.value,
              })
            }
          />
        </div>
      </div>
      <button
        className="btn"
        onClick={handleRollingPrediction}
        disabled={loading}
        style={{ marginTop: "15px" }}
      >
        🔄 开始滚动预测
      </button>
      <div className="info-card" style={{ marginTop: "15px" }}>
        <p style={{ margin: 0, fontSize: "13px", color: "#1e40af" }}>
          💡 <strong>说明：</strong>
          持续更新预测结果，评估预测稳定性。每次迭代将预测结果作为新的观测数据重新预测。
        </p>
      </div>
    </div>
  );

  // 渲染虚拟观测点预测表单
  const renderVirtualForm = () => (
    <div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 1fr",
          gap: "15px",
        }}
      >
        <div className="form-group">
          <label>台风编号</label>
          <input
            type="text"
            placeholder="例如: 2601 或 202601"
            value={virtualForm.typhoonId}
            onChange={(e) =>
              setVirtualForm({ ...virtualForm, typhoonId: e.target.value })
            }
          />
        </div>
        <div className="form-group">
          <label>预报时效（小时）</label>
          <select
            value={virtualForm.hours}
            onChange={(e) =>
              setVirtualForm({ ...virtualForm, hours: e.target.value })
            }
          >
            <option value={12}>12小时</option>
            <option value={24}>24小时</option>
            <option value={48}>48小时</option>
            <option value={72}>72小时</option>
            <option value={120}>120小时</option>
          </select>
        </div>
      </div>

      <div style={{ marginTop: "20px" }}>
        <h4>虚拟观测点</h4>
        {virtualForm.virtualObservations.map((obs, index) => (
          <div
            key={index}
            style={{
              display: "grid",
              gridTemplateColumns: "2fr 1fr 1fr auto",
              gap: "10px",
              marginTop: "10px",
              alignItems: "end",
            }}
          >
            <div className="form-group">
              <label>时间</label>
              <input
                type="datetime-local"
                value={obs.timestamp}
                onChange={(e) =>
                  updateVirtualObservation(index, "timestamp", e.target.value)
                }
              />
            </div>
            <div className="form-group">
              <label>纬度</label>
              <input
                type="number"
                step="0.01"
                placeholder="例如: 20.5"
                value={obs.latitude}
                onChange={(e) =>
                  updateVirtualObservation(index, "latitude", e.target.value)
                }
              />
            </div>
            <div className="form-group">
              <label>经度</label>
              <input
                type="number"
                step="0.01"
                placeholder="例如: 125.8"
                value={obs.longitude}
                onChange={(e) =>
                  updateVirtualObservation(index, "longitude", e.target.value)
                }
              />
            </div>
            <button
              className="btn btn-danger"
              onClick={() => removeVirtualObservation(index)}
              disabled={virtualForm.virtualObservations.length <= 1}
              style={{
                padding: "8px 12px",
                background: "#ef4444",
                color: "white",
              }}
            >
              删除
            </button>
          </div>
        ))}
        <button
          className="btn"
          onClick={addVirtualObservation}
          style={{
            marginTop: "10px",
            background: "#10b981",
            color: "white",
          }}
        >
          + 添加观测点
        </button>
      </div>

      <button
        className="btn"
        onClick={handleVirtualPrediction}
        disabled={loading}
        style={{ marginTop: "20px" }}
      >
        🎭 开始虚拟观测点预测
      </button>
      <div className="info-card" style={{ marginTop: "15px" }}>
        <p style={{ margin: 0, fontSize: "13px", color: "#1e40af" }}>
          💡 <strong>说明：</strong>
          基于假设的观测点进行预测。用于&quot;如果台风转向...&quot;等假设情景分析。
        </p>
      </div>
    </div>
  );

  return (
    <div>
      <h2>🎯 智能预测</h2>

      {/* 预测类型选择 */}
      <div className="form-group">
        <label>预测类型</label>
        <select
          value={predictionType}
          onChange={(e) => {
            setPredictionType(e.target.value);
            setResult(null);
            setError(null);
          }}
        >
          <option value="path">路径预测</option>
          <option value="arbitrary">任意起点预测</option>
          <option value="rolling">滚动预测</option>
          <option value="virtual">虚拟观测点预测</option>
        </select>
      </div>

      {/* 根据类型渲染不同表单 */}
      {predictionType === "path" && renderPathForm()}
      {predictionType === "arbitrary" && renderArbitraryForm()}
      {predictionType === "rolling" && renderRollingForm()}
      {predictionType === "virtual" && renderVirtualForm()}

      {/* 错误提示 */}
      {error && (
        <div className="error-message" style={{ marginTop: "20px" }}>
          ❌ {error}
        </div>
      )}

      {/* 加载状态 */}
      {loading && (
        <div className="loading" style={{ marginTop: "20px" }}>
          <div className="spinner"></div>
          <p>AI模型预测中，请稍候...</p>
        </div>
      )}

      {/* 结果显示 */}
      {result && (
        <div style={{ marginTop: "20px" }}>
          {(result.type === "path" ||
            result.type === "arbitrary" ||
            result.type === "virtual") &&
            renderPredictionTable(result.data, true)}
          {result.type === "rolling" && renderRollingResult(result.data)}
        </div>
      )}
    </div>
  );
}

export default Prediction;
