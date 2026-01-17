/**
 * 图像分析组件（重构版本）
 *
 * 重构说明：
 * - 支持新的分析类型：basic/advanced/opencv/fusion
 * - 支持图像类型选择：infrared/visible
 * - 显示详细的分析结果（台风中心、强度、台风眼、螺旋结构等）
 */
import React, { useState } from "react";
import axios from "axios";
import "../styles/ImageAnalysis.css";
import "../styles/common.css";

const API_BASE_URL = "http://localhost:8000/api";

function ImageAnalysis() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [uploadedImageId, setUploadedImageId] = useState(null);

  // 图像分析表单
  const [analysisForm, setAnalysisForm] = useState({
    typhoonId: "",
    imageFile: null,
    analysisType: "fusion", // 默认使用混合方案
    imageType: "infrared", // 默认红外图
  });

  // 处理文件选择
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setAnalysisForm({ ...analysisForm, imageFile: file });
      setError(null);
    }
  };

  // 处理图像上传
  const handleUpload = async () => {
    if (!analysisForm.imageFile) {
      alert("请选择图像文件");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const formData = new FormData();
      formData.append("file", analysisForm.imageFile);
      if (analysisForm.typhoonId) {
        formData.append("typhoon_id", analysisForm.typhoonId);
      }
      formData.append("image_type", "satellite");

      const response = await axios.post(
        `${API_BASE_URL}/images/upload`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      setUploadedImageId(response.data.image_id);
      alert(`图像上传成功！图像ID: ${response.data.image_id}`);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "图像上传失败");
    } finally {
      setLoading(false);
    }
  };

  // 处理图像分析
  const handleAnalysis = async () => {
    if (!uploadedImageId) {
      alert("请先上传图像");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await axios.post(
        `${API_BASE_URL}/images/analyze/${uploadedImageId}?analysis_type=${analysisForm.analysisType}&image_type=${analysisForm.imageType}`
      );

      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "图像分析失败");
    } finally {
      setLoading(false);
    }
  };

  // 渲染分析结果
  const renderResult = () => {
    if (!result) return null;

    return (
      <div className="info-card" style={{ marginTop: "20px" }}>
        <h4>🖼️ 图像分析结果</h4>

        {/* 基本信息 */}
        <div style={{ marginBottom: "20px" }}>
          <p>
            <strong>图像ID:</strong> {result.image_id}
          </p>
          <p>
            <strong>分析类型:</strong> {result.analysis_type}
          </p>
          <p>
            <strong>分析方法:</strong> {result.method}
          </p>
          <p>
            <strong>综合置信度:</strong>{" "}
            <span
              style={{
                color:
                  result.confidence >= 0.8
                    ? "#10b981"
                    : result.confidence >= 0.6
                    ? "#f59e0b"
                    : "#ef4444",
                fontWeight: "bold",
              }}
            >
              {(result.confidence * 100).toFixed(1)}%
            </span>
          </p>
          <p>
            <strong>处理时间:</strong> {result.processing_time?.toFixed(2)}秒
          </p>
          <p>
            <strong>分析时间:</strong>{" "}
            {new Date(result.analyzed_at).toLocaleString("zh-CN")}
          </p>
        </div>

        {/* 台风中心 */}
        {result.center && (
          <div style={{ marginBottom: "20px" }}>
            <h5>📍 台风中心位置</h5>
            <div
              style={{
                background: "#f9fafb",
                padding: "15px",
                borderRadius: "8px",
              }}
            >
              <p>
                <strong>坐标:</strong> ({result.center.pixel_x?.toFixed(1)},{" "}
                {result.center.pixel_y?.toFixed(1)}) 像素
              </p>
              <p>
                <strong>置信度:</strong>{" "}
                {(result.center.confidence * 100).toFixed(1)}%
              </p>
              {result.center.method && (
                <p>
                  <strong>检测方法:</strong> {result.center.method}
                </p>
              )}
            </div>
          </div>
        )}

        {/* 强度评估 */}
        {result.intensity && (
          <div style={{ marginBottom: "20px" }}>
            <h5>💨 强度评估</h5>
            <div
              style={{
                background: "#f9fafb",
                padding: "15px",
                borderRadius: "8px",
              }}
            >
              <p>
                <strong>强度等级:</strong>{" "}
                <span
                  style={{
                    fontSize: "18px",
                    fontWeight: "bold",
                    color: "#dc2626",
                  }}
                >
                  {result.intensity.level}
                </span>
              </p>
              <p>
                <strong>置信度:</strong>{" "}
                {(result.intensity.confidence * 100).toFixed(1)}%
              </p>
              {result.intensity.method && (
                <p>
                  <strong>评估方法:</strong> {result.intensity.method}
                </p>
              )}
            </div>
          </div>
        )}

        {/* 台风眼 */}
        {result.eye && (
          <div style={{ marginBottom: "20px" }}>
            <h5>👁️ 台风眼检测</h5>
            <div
              style={{
                background: "#f9fafb",
                padding: "15px",
                borderRadius: "8px",
              }}
            >
              <p>
                <strong>检测结果:</strong>{" "}
                {result.eye.detected ? (
                  <span style={{ color: "#10b981", fontWeight: "bold" }}>
                    ✅ 检测到台风眼
                  </span>
                ) : (
                  <span style={{ color: "#6b7280" }}>❌ 未检测到台风眼</span>
                )}
              </p>
              {result.eye.detected && result.eye.diameter_km && (
                <p>
                  <strong>台风眼直径:</strong>{" "}
                  {result.eye.diameter_km.toFixed(1)} 公里
                </p>
              )}
              <p>
                <strong>置信度:</strong>{" "}
                {(result.eye.confidence * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        )}

        {/* 螺旋结构 */}
        {result.structure && (
          <div style={{ marginBottom: "20px" }}>
            <h5>🌀 螺旋结构分析</h5>
            <div
              style={{
                background: "#f9fafb",
                padding: "15px",
                borderRadius: "8px",
              }}
            >
              <p>
                <strong>螺旋结构评分:</strong>{" "}
                {(result.structure.spiral_score * 100).toFixed(1)}%
              </p>
              {result.structure.organization && (
                <p>
                  <strong>组织程度:</strong> {result.structure.organization}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div>
      <h2>🖼️ 图像分析（重构版本）</h2>

      <h3>卫星云图分析</h3>

      {/* 台风ID输入 */}
      <div className="form-group">
        <label>台风ID（可选）</label>
        <input
          type="text"
          placeholder="例如: 2501"
          value={analysisForm.typhoonId}
          onChange={(e) =>
            setAnalysisForm({ ...analysisForm, typhoonId: e.target.value })
          }
        />
      </div>

      {/* 图像文件上传 */}
      <div className="form-group">
        <label>上传图像文件</label>
        <input
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          style={{ padding: "8px" }}
        />
        {analysisForm.imageFile && (
          <p style={{ marginTop: "8px", color: "#10b981", fontSize: "14px" }}>
            ✅ 已选择: {analysisForm.imageFile.name}
          </p>
        )}
      </div>

      {/* 上传按钮 */}
      <button
        className="btn"
        onClick={handleUpload}
        disabled={loading || !analysisForm.imageFile}
        style={{ marginBottom: "15px" }}
      >
        📤 上传图像
      </button>

      {uploadedImageId && (
        <div
          className="info-card"
          style={{ marginBottom: "15px", background: "#ecfdf5" }}
        >
          <p style={{ margin: 0, color: "#10b981" }}>
            ✅ 图像已上传，ID: {uploadedImageId}
          </p>
        </div>
      )}

      {/* 分析类型选择 */}
      <div className="form-group">
        <label>分析类型</label>
        <select
          value={analysisForm.analysisType}
          onChange={(e) =>
            setAnalysisForm({ ...analysisForm, analysisType: e.target.value })
          }
          style={{ padding: "10px", fontSize: "14px" }}
        >
          <option value="fusion">混合方案（推荐）⭐</option>
          <option value="opencv">OpenCV传统方法</option>
          <option value="advanced">高级特征提取</option>
          <option value="basic">基础统计分析</option>
        </select>
        <p style={{ marginTop: "8px", fontSize: "13px", color: "#6b7280" }}>
          {analysisForm.analysisType === "fusion" &&
            "🔥 混合方案：结合OpenCV传统方法和深度学习，准确率最高"}
          {analysisForm.analysisType === "opencv" &&
            "🔧 OpenCV方法：基于传统图像处理，无需训练数据"}
          {analysisForm.analysisType === "advanced" &&
            "📊 高级分析：提取详细的图像特征"}
          {analysisForm.analysisType === "basic" && "📈 基础分析：快速统计分析"}
        </p>
      </div>

      {/* 图像类型选择 */}
      <div className="form-group">
        <label>图像类型</label>
        <select
          value={analysisForm.imageType}
          onChange={(e) =>
            setAnalysisForm({ ...analysisForm, imageType: e.target.value })
          }
          style={{ padding: "10px", fontSize: "14px" }}
        >
          <option value="infrared">红外卫星云图</option>
          <option value="visible">可见光卫星云图</option>
        </select>
        <p style={{ marginTop: "8px", fontSize: "13px", color: "#6b7280" }}>
          {analysisForm.imageType === "infrared" &&
            "🌡️ 红外图：显示云顶温度，适合夜间观测"}
          {analysisForm.imageType === "visible" &&
            "☀️ 可见光图：显示云层反射率，适合白天观测"}
        </p>
      </div>

      {/* 分析按钮 */}
      <button
        className="btn"
        onClick={handleAnalysis}
        disabled={loading || !uploadedImageId}
      >
        🔍 开始分析
      </button>

      {/* 功能说明 */}
      <div className="info-card" style={{ marginTop: "15px" }}>
        <p style={{ margin: 0, fontSize: "13px", color: "#1e40af" }}>
          💡 <strong>功能说明：</strong>
        </p>
        <ul
          style={{ margin: "8px 0 0 20px", fontSize: "12px", color: "#1e40af" }}
        >
          <li>支持分析台风卫星云图（红外图/可见光图）</li>
          <li>
            <strong>混合方案</strong>：结合OpenCV传统方法和深度学习模型
          </li>
          <li>提供台风中心位置、强度评估、台风眼检测、螺旋结构分析</li>
          <li>显示详细的置信度和分析方法信息</li>
          <li>处理速度：1-3秒/张，准确率：60-90%</li>
        </ul>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="error-message" style={{ marginTop: "20px" }}>
          ❌ {error}
        </div>
      )}

      {/* 加载状态 */}
      {loading && <div className="loading">处理中...</div>}

      {/* 结果显示 */}
      {result && renderResult()}
    </div>
  );
}

export default ImageAnalysis;
