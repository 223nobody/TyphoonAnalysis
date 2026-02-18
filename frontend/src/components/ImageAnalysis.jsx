/**
 * 图像分析组件
 *
 * 重构说明：
 * - 支持新的分析类型：basic/advanced/opencv/fusion
 * - 支持图像类型选择：infrared/visible
 * - 显示详细的分析结果（台风中心、强度、台风眼、螺旋结构等）
 * - 新增视频分析功能：支持视频上传、AI视频分析
 * - 美化UI，支持拖放上传
 */
import React, { useState, useRef } from "react";
import { marked } from "marked";
marked.setOptions({
  async: false,
});
import {
  uploadImage,
  analyzeImage,
  uploadAndAnalyzeVideo,
} from "../services/api";
import "../styles/ImageAnalysis.css";
import "../styles/common.css";

function ImageAnalysis() {
  // ============ 图像分析状态 ============
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [uploadedImageId, setUploadedImageId] = useState(null);
  const [imageDragOver, setImageDragOver] = useState(false);
  const imageInputRef = useRef(null);

  const [analysisForm, setAnalysisForm] = useState({
    typhoonId: "",
    imageFile: null,
    analysisType: "fusion",
    imageType: "infrared",
  });

  // ============ 视频分析状态 ============
  const [activeTab, setActiveTab] = useState("image");
  const [videoFile, setVideoFile] = useState(null);
  const [analysisId, setAnalysisId] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [videoResult, setVideoResult] = useState(null);
  const [videoError, setVideoError] = useState(null);
  const [videoDragOver, setVideoDragOver] = useState(false);
  const videoInputRef = useRef(null);

  const [videoAnalysisConfig, setVideoAnalysisConfig] = useState({
    analysisType: "comprehensive",
    extractFrames: true,
    frameInterval: 1,
  });

  // ============ 工具函数 ============
  const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  // ============ 图像分析处理函数 ============
  const handleImageFile = (file) => {
    if (!file) return;
    setAnalysisForm({ ...analysisForm, imageFile: file });
    setError(null);
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    handleImageFile(file);
  };

  const handleImageDragOver = (e) => {
    e.preventDefault();
    setImageDragOver(true);
  };

  const handleImageDragLeave = (e) => {
    e.preventDefault();
    setImageDragOver(false);
  };

  const handleImageDrop = (e) => {
    e.preventDefault();
    setImageDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) {
      handleImageFile(file);
    }
  };

  const handleImageUploadClick = () => {
    imageInputRef.current?.click();
  };

  const handleUpload = async () => {
    if (!analysisForm.imageFile) {
      alert("请选择图像文件");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const data = await uploadImage(
        analysisForm.imageFile,
        analysisForm.typhoonId,
      );

      setUploadedImageId(data.image_id);
      alert(`图像上传成功！图像ID: ${data.image_id}`);
    } catch (err) {
      setError(err.message || "图像上传失败");
    } finally {
      setLoading(false);
    }
  };

  const handleAnalysis = async () => {
    if (!uploadedImageId) {
      alert("请先上传图像");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const data = await analyzeImage(
        uploadedImageId,
        analysisForm.analysisType,
        analysisForm.imageType,
      );

      setResult(data);
    } catch (err) {
      setError(err.message || "图像分析失败");
    } finally {
      setLoading(false);
    }
  };

  // ============ 视频分析处理函数 ============
  const handleVideoFile = (file) => {
    if (!file) return;

    const validTypes = [
      "video/mp4",
      "video/avi",
      "video/mov",
      "video/wmv",
      "video/webm",
    ];
    if (!validTypes.includes(file.type)) {
      setVideoError("请上传有效的视频文件 (MP4, AVI, MOV, WMV, WEBM)");
      return;
    }
    if (file.size > 500 * 1024 * 1024) {
      setVideoError("视频文件大小不能超过500MB");
      return;
    }
    setVideoFile(file);
    setVideoError(null);
    setAnalysisId(null);
    setVideoResult(null);
  };

  const handleVideoFileChange = (e) => {
    const file = e.target.files[0];
    handleVideoFile(file);
  };

  const handleVideoDragOver = (e) => {
    e.preventDefault();
    setVideoDragOver(true);
  };

  const handleVideoDragLeave = (e) => {
    e.preventDefault();
    setVideoDragOver(false);
  };

  const handleVideoDrop = (e) => {
    e.preventDefault();
    setVideoDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("video/")) {
      handleVideoFile(file);
    }
  };

  const handleVideoUploadClick = () => {
    videoInputRef.current?.click();
  };

  const handleVideoAnalysis = async () => {
    if (!videoFile) {
      alert("请选择视频文件");
      return;
    }

    try {
      setIsAnalyzing(true);
      setVideoError(null);
      setVideoResult(null);

      const data = await uploadAndAnalyzeVideo(
        videoFile,
        videoAnalysisConfig.analysisType,
        videoAnalysisConfig.extractFrames,
        videoAnalysisConfig.frameInterval,
      );

      if (data.success && data.analysis_id) {
        setAnalysisId(data.analysis_id);
        setVideoResult(data);
      } else {
        setVideoError(data.error || "分析失败");
      }
    } catch (err) {
      setVideoError(err.message || "视频分析失败");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // ============ 渲染函数 ============
  const renderImageResult = () => {
    if (!result) return null;

    return (
      <div className="info-card" style={{ marginTop: "20px" }}>
        <h4>图像分析结果</h4>
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
        </div>

        {result.center && (
          <div style={{ marginBottom: "20px" }}>
            <h5>台风中心位置</h5>
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
            </div>
          </div>
        )}

        {result.intensity && (
          <div style={{ marginBottom: "20px" }}>
            <h5>强度评估</h5>
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
            </div>
          </div>
        )}

        {result.eye && (
          <div style={{ marginBottom: "20px" }}>
            <h5>台风眼检测</h5>
            <div
              style={{
                background: "#f9fafb",
                padding: "15px",
                borderRadius: "8px",
              }}
            >
              <p>
                <strong>检测结果:</strong>{" "}
                {result.eye.detected ? "检测到台风眼" : "未检测到台风眼"}
              </p>
              <p>
                <strong>置信度:</strong>{" "}
                {(result.eye.confidence * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderVideoResult = () => {
    if (!videoResult) return null;

    const aiAnalysis = videoResult.ai_analysis;
    let reportContent = "";

    if (aiAnalysis) {
      if (typeof aiAnalysis === "string") {
        reportContent = aiAnalysis;
      } else if (aiAnalysis.description) {
        const desc = aiAnalysis.description;
        if (typeof desc === "string") {
          reportContent = desc;
        } else if (Array.isArray(desc)) {
          reportContent = desc
            .map((item) => {
              if (typeof item === "string") return item;
              if (item && item.text) return item.text;
              return JSON.stringify(item);
            })
            .join("\n");
        } else if (typeof desc === "object") {
          reportContent = JSON.stringify(desc, null, 2);
        } else {
          reportContent = String(desc);
        }
      } else {
        reportContent = JSON.stringify(aiAnalysis, null, 2);
      }
    }

    const formattedTime = videoResult.created_at
      ? new Date(videoResult.created_at).toLocaleString("zh-CN", {
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        })
      : null;

    return (
      <div className="info-card" style={{ marginTop: "20px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "15px",
            flexWrap: "wrap",
            gap: "10px",
          }}
        >
          <h3>📹 视频分析报告</h3>
          <div style={{ display: "flex", gap: "10px" }}>
            {reportContent && (
              <button
                className="btn"
                onClick={() => {
                  const blob = new Blob([reportContent], {
                    type: "text/markdown",
                  });
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `video_analysis_${videoResult.analysis_id}.md`;
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  window.URL.revokeObjectURL(url);
                }}
                style={{ padding: "8px 15px", fontSize: "14px" }}
              >
                📥 下载报告
              </button>
            )}
          </div>
        </div>

        <div
          style={{
            marginBottom: "20px",
            padding: "15px",
            background: "#f9fafb",
            borderRadius: "8px",
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "10px",
          }}
        >
          <div>
            <span style={{ fontWeight: 600, color: "#666" }}>🆔 分析ID:</span>
            <span style={{ marginLeft: "8px" }}>{videoResult.analysis_id}</span>
          </div>
          <div>
            <span style={{ fontWeight: 600, color: "#666" }}>📊 分析类型:</span>
            <span style={{ marginLeft: "8px" }}>
              {videoResult.analysis_type === "comprehensive" && "综合分析"}
              {videoResult.analysis_type === "tracking" && "台风追踪"}
              {videoResult.analysis_type === "intensity" && "强度评估"}
              {videoResult.analysis_type === "structure" && "结构分析"}
            </span>
          </div>
          <div>
            <span style={{ fontWeight: 600, color: "#666" }}>📈 状态:</span>
            <span
              style={{
                marginLeft: "8px",
                fontWeight: "bold",
                color:
                  videoResult.status === "completed"
                    ? "#10b981"
                    : videoResult.status === "processing"
                      ? "#f59e0b"
                      : "#ef4444",
              }}
            >
              {videoResult.status === "completed"
                ? "分析完成"
                : videoResult.status === "processing"
                  ? "分析中"
                  : "分析失败"}
            </span>
          </div>
          {videoResult.processing_time && (
            <div>
              <span style={{ fontWeight: 600, color: "#666" }}>
                ⏱️ 处理时间:
              </span>
              <span style={{ marginLeft: "8px" }}>
                {videoResult.processing_time.toFixed(2)}秒
              </span>
            </div>
          )}
          {formattedTime && (
            <div>
              <span style={{ fontWeight: 600, color: "#666" }}>
                🕐 分析时间:
              </span>
              <span style={{ marginLeft: "8px" }}>{formattedTime}</span>
            </div>
          )}
          {videoResult.frame_count > 0 && (
            <div>
              <span style={{ fontWeight: 600, color: "#666" }}>
                🎞️ 分析帧数:
              </span>
              <span style={{ marginLeft: "8px" }}>
                {videoResult.frame_count} 帧
              </span>
            </div>
          )}
        </div>

        {reportContent ? (
          <div className="content-section">
            <div
              className="content-text markdown-body"
              style={{
                background: "white",
                padding: "20px",
                borderRadius: "8px",
                border: "1px solid #e5e7eb",
                maxHeight: "600px",
                overflowY: "auto",
                lineHeight: "1.6",
              }}
              dangerouslySetInnerHTML={{
                __html: (() => {
                  try {
                    return marked.parse(reportContent);
                  } catch (e) {
                    console.error("marked.parse error:", e);
                    return `<pre>${reportContent}</pre>`;
                  }
                })(),
              }}
            />
          </div>
        ) : videoResult.error ? (
          <div
            style={{
              padding: "15px",
              background: "#fef2f2",
              borderRadius: "8px",
              color: "#ef4444",
            }}
          >
            <h4>❌ 分析失败</h4>
            <p>{videoResult.error}</p>
          </div>
        ) : (
          <div
            style={{
              padding: "15px",
              background: "#fef3c7",
              borderRadius: "8px",
              color: "#f59e0b",
            }}
          >
            <h4>⚠️ 提示</h4>
            <p>暂无分析内容</p>
          </div>
        )}
      </div>
    );
  };

  return (
    <div>
      <h2>图像与视频分析</h2>

      <div
        style={{
          display: "flex",
          gap: "8px",
          marginBottom: "24px",
          background: "#f3f4f6",
          padding: "6px",
          borderRadius: "12px",
        }}
      >
        <button
          onClick={() => setActiveTab("image")}
          style={{
            flex: 1,
            padding: "12px 20px",
            fontSize: "15px",
            fontWeight: 600,
            border: "none",
            borderRadius: "8px",
            background: activeTab === "image" ? "#ffffff" : "transparent",
            color: activeTab === "image" ? "#1f2937" : "#6b7280",
            cursor: "pointer",
            boxShadow: activeTab === "image" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
            transition: "all 0.2s",
          }}
        >
          🖼️ 图像分析
        </button>
        <button
          onClick={() => setActiveTab("video")}
          style={{
            flex: 1,
            padding: "12px 20px",
            fontSize: "15px",
            fontWeight: 600,
            border: "none",
            borderRadius: "8px",
            background: activeTab === "video" ? "#ffffff" : "transparent",
            color: activeTab === "video" ? "#1f2937" : "#6b7280",
            cursor: "pointer",
            boxShadow: activeTab === "video" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
            transition: "all 0.2s",
          }}
        >
          🎬 视频分析
        </button>
      </div>

      {activeTab === "image" && (
        <div>
          <h3 style={{ marginBottom: "20px" }}>卫星云图分析</h3>

          <div className="form-group">
            <label style={{ fontWeight: 600, marginBottom: "8px", display: "block" }}>
              台风ID（可选）
            </label>
            <input
              type="text"
              placeholder="例如: 2501"
              value={analysisForm.typhoonId}
              onChange={(e) =>
                setAnalysisForm({ ...analysisForm, typhoonId: e.target.value })
              }
              style={{
                padding: "12px 16px",
                borderRadius: "8px",
                border: "1px solid #e5e7eb",
                fontSize: "14px",
              }}
            />
          </div>

          <div className="form-group">
            <label style={{ fontWeight: 600, marginBottom: "8px", display: "block" }}>
              上传图像文件
            </label>
            <input
              ref={imageInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />
            <div
              onClick={handleImageUploadClick}
              onDragOver={handleImageDragOver}
              onDragLeave={handleImageDragLeave}
              onDrop={handleImageDrop}
              style={{
                padding: "40px 20px",
                border: `2px dashed ${imageDragOver ? "#3b82f6" : "#d1d5db"}`,
                borderRadius: "12px",
                background: imageDragOver ? "#eff6ff" : "#fafafa",
                textAlign: "center",
                cursor: "pointer",
                transition: "all 0.2s",
              }}
            >
              {analysisForm.imageFile ? (
                <div>
                  <div style={{ fontSize: "40px", marginBottom: "12px" }}>📄</div>
                  <p style={{ fontWeight: 600, marginBottom: "4px" }}>
                    {analysisForm.imageFile.name}
                  </p>
                  <p style={{ fontSize: "13px", color: "#6b7280" }}>
                    {formatFileSize(analysisForm.imageFile.size)}
                  </p>
                  <p style={{ fontSize: "13px", color: "#3b82f6", marginTop: "8px" }}>
                    点击或拖放更换文件
                  </p>
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: "40px", marginBottom: "12px" }}>🖼️</div>
                  <p style={{ fontWeight: 600, marginBottom: "4px" }}>
                    点击或拖放上传图像
                  </p>
                  <p style={{ fontSize: "13px", color: "#6b7280" }}>
                    支持 JPG, PNG, GIF, WebP 等格式
                  </p>
                </div>
              )}
            </div>
          </div>

          <button
            className="btn"
            onClick={handleUpload}
            disabled={loading || !analysisForm.imageFile}
            style={{
              width: "100%",
              padding: "14px 20px",
              fontSize: "15px",
              fontWeight: 600,
              marginBottom: "15px",
            }}
          >
            {loading ? "上传中..." : "上传图像"}
          </button>

          {uploadedImageId && (
            <div
              className="info-card"
              style={{
                marginBottom: "15px",
                background: "#ecfdf5",
                border: "1px solid #a7f3d0",
                borderRadius: "8px",
              }}
            >
              <p style={{ margin: 0, color: "#10b981" }}>
                ✅ 图像已上传，ID: {uploadedImageId}
              </p>
            </div>
          )}

          <div className="form-group">
            <label style={{ fontWeight: 600, marginBottom: "8px", display: "block" }}>
              分析类型
            </label>
            <select
              value={analysisForm.analysisType}
              onChange={(e) =>
                setAnalysisForm({
                  ...analysisForm,
                  analysisType: e.target.value,
                })
              }
              style={{
                padding: "12px 16px",
                borderRadius: "8px",
                border: "1px solid #e5e7eb",
                fontSize: "14px",
                background: "white",
              }}
            >
              <option value="fusion">混合方案（推荐）</option>
              <option value="opencv">OpenCV传统方法</option>
              <option value="advanced">高级特征提取</option>
              <option value="basic">基础统计分析</option>
            </select>
          </div>

          <div className="form-group">
            <label style={{ fontWeight: 600, marginBottom: "8px", display: "block" }}>
              图像类型
            </label>
            <select
              value={analysisForm.imageType}
              onChange={(e) =>
                setAnalysisForm({ ...analysisForm, imageType: e.target.value })
              }
              style={{
                padding: "12px 16px",
                borderRadius: "8px",
                border: "1px solid #e5e7eb",
                fontSize: "14px",
                background: "white",
              }}
            >
              <option value="infrared">红外卫星云图</option>
              <option value="visible">可见光卫星云图</option>
            </select>
          </div>

          <button
            className="btn"
            onClick={handleAnalysis}
            disabled={loading || !uploadedImageId}
            style={{ width: "100%", padding: "14px 20px", fontSize: "15px", fontWeight: 600 }}
          >
            {loading ? "分析中..." : "开始分析"}
          </button>

          {error && (
            <div className="error-message" style={{ marginTop: "20px", borderRadius: "8px" }}>
              {error}
            </div>
          )}

          {loading && <div className="loading" style={{ borderRadius: "8px" }}>处理中...</div>}

          {renderImageResult()}
        </div>
      )}

      {activeTab === "video" && (
        <div>
          <h3 style={{ marginBottom: "20px" }}>视频内容分析</h3>

          <div className="form-group">
            <label style={{ fontWeight: 600, marginBottom: "8px", display: "block" }}>
              上传视频文件
            </label>
            <input
              ref={videoInputRef}
              type="file"
              accept="video/*"
              onChange={handleVideoFileChange}
              style={{ display: "none" }}
              disabled={isAnalyzing}
            />
            <div
              onClick={!isAnalyzing ? handleVideoUploadClick : undefined}
              onDragOver={!isAnalyzing ? handleVideoDragOver : undefined}
              onDragLeave={!isAnalyzing ? handleVideoDragLeave : undefined}
              onDrop={!isAnalyzing ? handleVideoDrop : undefined}
              style={{
                padding: "40px 20px",
                border: `2px dashed ${videoDragOver ? "#3b82f6" : "#d1d5db"}`,
                borderRadius: "12px",
                background: isAnalyzing ? "#f3f4f6" : videoDragOver ? "#eff6ff" : "#fafafa",
                textAlign: "center",
                cursor: isAnalyzing ? "not-allowed" : "pointer",
                transition: "all 0.2s",
                opacity: isAnalyzing ? 0.6 : 1,
              }}
            >
              {videoFile ? (
                <div>
                  <div style={{ fontSize: "40px", marginBottom: "12px" }}>🎬</div>
                  <p style={{ fontWeight: 600, marginBottom: "4px" }}>
                    {videoFile.name}
                  </p>
                  <p style={{ fontSize: "13px", color: "#6b7280" }}>
                    {formatFileSize(videoFile.size)}
                  </p>
                  {!isAnalyzing && (
                    <p style={{ fontSize: "13px", color: "#3b82f6", marginTop: "8px" }}>
                      点击或拖放更换文件
                    </p>
                  )}
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: "40px", marginBottom: "12px" }}>📁</div>
                  <p style={{ fontWeight: 600, marginBottom: "4px" }}>
                    点击或拖放上传视频
                  </p>
                  <p style={{ fontSize: "13px", color: "#6b7280" }}>
                    支持 MP4, AVI, MOV, WMV, WEBM 格式（最大 500MB）
                  </p>
                </div>
              )}
            </div>
          </div>

          {videoError && (
            <div className="error-message" style={{ marginBottom: "15px", borderRadius: "8px" }}>
              {videoError}
            </div>
          )}

          {analysisId && (
            <div
              className="info-card"
              style={{
                marginBottom: "15px",
                background: "#ecfdf5",
                border: "1px solid #a7f3d0",
                borderRadius: "8px",
              }}
            >
              <p style={{ margin: 0, color: "#10b981" }}>
                ✅ 分析记录ID: {analysisId}
              </p>
            </div>
          )}

          <div className="form-group">
            <label style={{ fontWeight: 600, marginBottom: "8px", display: "block" }}>
              分析类型
            </label>
            <select
              value={videoAnalysisConfig.analysisType}
              onChange={(e) =>
                setVideoAnalysisConfig({
                  ...videoAnalysisConfig,
                  analysisType: e.target.value,
                })
              }
              style={{
                padding: "12px 16px",
                borderRadius: "8px",
                border: "1px solid #e5e7eb",
                fontSize: "14px",
                background: "white",
              }}
            >
              <option value="comprehensive">综合分析</option>
              <option value="tracking">台风追踪</option>
              <option value="intensity">强度评估</option>
              <option value="structure">结构分析</option>
            </select>
          </div>

          <div className="form-group">
            <label
              style={{
                display: "flex",
                alignItems: "center",
                cursor: "pointer",
                fontWeight: 600,
                gap: "8px",
              }}
            >
              <input
                type="checkbox"
                checked={videoAnalysisConfig.extractFrames}
                onChange={(e) =>
                  setVideoAnalysisConfig({
                    ...videoAnalysisConfig,
                    extractFrames: e.target.checked,
                  })
                }
                style={{
                  width: "18px",
                  height: "18px",
                  accentColor: "#3b82f6",
                }}
              />
              提取关键帧进行分析
            </label>
          </div>

          {videoAnalysisConfig.extractFrames && (
            <div className="form-group">
              <label style={{ fontWeight: 600, marginBottom: "8px", display: "block" }}>
                帧提取间隔（秒）
              </label>
              <input
                type="number"
                min="0.5"
                max="60"
                step="0.5"
                value={videoAnalysisConfig.frameInterval}
                onChange={(e) =>
                  setVideoAnalysisConfig({
                    ...videoAnalysisConfig,
                    frameInterval: parseFloat(e.target.value) || 1,
                  })
                }
                style={{
                  padding: "12px 16px",
                  borderRadius: "8px",
                  border: "1px solid #e5e7eb",
                  fontSize: "14px",
                  width: "120px",
                }}
              />
            </div>
          )}

          <button
            className="btn"
            onClick={handleVideoAnalysis}
            disabled={isAnalyzing || !videoFile}
            style={{
              width: "100%",
              padding: "14px 20px",
              fontSize: "15px",
              fontWeight: 600,
            }}
          >
            {isAnalyzing ? "分析中..." : "上传并分析"}
          </button>

          {isAnalyzing && (
            <div className="loading" style={{ marginTop: "20px", borderRadius: "8px" }}>
              视频上传并分析中，请稍候...
            </div>
          )}

          {renderVideoResult()}
        </div>
      )}
    </div>
  );
}

export default ImageAnalysis;
