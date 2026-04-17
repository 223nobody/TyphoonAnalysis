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
import { useEffect, useRef, useState } from "react";
import { marked } from "marked";
marked.setOptions({
  async: false,
});
import html2pdf from "html2pdf.js";
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
  const [uploadInfo, setUploadInfo] = useState(null);
  const [uploadPreviewUrl, setUploadPreviewUrl] = useState("");
  const [uploadToast, setUploadToast] = useState(null);
  const [imageDragOver, setImageDragOver] = useState(false);
  const imageInputRef = useRef(null);
  const imageReportContentRef = useRef(null);

  const [analysisForm, setAnalysisForm] = useState({
    typhoonId: "",
    imageFile: null,
    analysisType: "hybrid_ai",
    imageType: "visible",
  });

  // ============ 视频分析状态 ============
  const [activeTab, setActiveTab] = useState("image");
  const [videoFile, setVideoFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [videoResult, setVideoResult] = useState(null);
  const [videoError, setVideoError] = useState(null);
  const [videoDragOver, setVideoDragOver] = useState(false);
  const videoInputRef = useRef(null);

  // PDF导出引用
  const videoReportContentRef = useRef(null);

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

  const formatDateTime = (value) => {
    if (!value) return null;
    return new Date(value).toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatPercentage = (value) => {
    if (typeof value !== "number") return "暂无";
    return `${(value * 100).toFixed(1)}%`;
  };

  useEffect(() => {
    if (!analysisForm.imageFile) {
      setUploadPreviewUrl("");
      return undefined;
    }

    const objectUrl = URL.createObjectURL(analysisForm.imageFile);
    setUploadPreviewUrl(objectUrl);

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [analysisForm.imageFile]);

  useEffect(() => {
    if (!uploadToast) return undefined;

    const timer = window.setTimeout(() => {
      setUploadToast(null);
    }, 2000);

    return () => {
      window.clearTimeout(timer);
    };
  }, [uploadToast]);

  const downloadMarkdown = (content, filename, emptyMessage) => {
    if (!content) {
      alert(emptyMessage);
      return;
    }

    const blob = new Blob([content], { type: "text/markdown" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  const exportElementToPdf = (elementRef, filename, emptyMessage) => {
    if (!elementRef.current) {
      alert(emptyMessage);
      return;
    }

    const timestamp = new Date().toISOString().slice(0, 10);
    const finalFilename = `${filename}_${timestamp}.pdf`;

    const opt = {
      margin: [15, 15, 15, 15],
      filename: finalFilename,
      image: { type: "jpeg", quality: 0.98 },
      html2canvas: {
        scale: 2,
        useCORS: true,
        letterRendering: true,
        scrollY: 0,
        scrollX: 0,
        windowHeight: document.documentElement.scrollHeight,
      },
      jsPDF: {
        unit: "mm",
        format: "a4",
        orientation: "portrait",
      },
      pagebreak: {
        mode: ["avoid-all", "css", "legacy"],
        before: ".page-break-before",
        after: ".page-break-after",
        avoid: ["h1", "h2", "h3", "h4", "h5", "h6", "table", "img"],
      },
    };

    const element = elementRef.current.cloneNode(true);
    const contentSections = element.querySelectorAll(".content-text");
    contentSections.forEach((section) => {
      section.style.maxHeight = "none";
      section.style.overflowY = "visible";
      section.style.height = "auto";
    });

    const style = document.createElement("style");
    style.textContent = `
      * {
        font-family: "Microsoft YaHei", "SimSun", sans-serif !important;
        box-sizing: border-box;
        margin: 0;
        padding: 0;
      }
      body {
        margin: 0;
        padding: 0;
      }
      h1 {
        page-break-after: avoid;
        page-break-inside: avoid;
        margin-top: 0.8em;
        margin-bottom: 0.4em;
        font-size: 1.8em;
        color: #1a202c;
      }
      h2 {
        page-break-after: avoid;
        page-break-inside: avoid;
        margin-top: 0.7em;
        margin-bottom: 0.35em;
        font-size: 1.5em;
        color: #1a202c;
      }
      h3 {
        page-break-after: avoid;
        page-break-inside: avoid;
        margin-top: 0.6em;
        margin-bottom: 0.3em;
        font-size: 1.3em;
        color: #1a202c;
      }
      h4, h5, h6 {
        page-break-after: avoid;
        page-break-inside: avoid;
        margin-top: 0.5em;
        margin-bottom: 0.25em;
        color: #1a202c;
      }
      p {
        line-height: 1.5;
        margin-top: 0.3em;
        margin-bottom: 0.3em;
        page-break-inside: avoid;
      }
      li {
        line-height: 1.4;
        margin-bottom: 0.2em;
        page-break-inside: avoid;
      }
      table {
        page-break-inside: avoid;
        width: 100%;
        border-collapse: collapse;
        margin: 0.5em 0;
      }
      table th, table td {
        border: 1px solid #ddd;
        padding: 6px 8px;
        text-align: left;
        line-height: 1.3;
      }
      img {
        max-width: 100%;
        page-break-inside: avoid;
        display: block;
        margin: 0.5em auto;
      }
      ul, ol {
        page-break-inside: avoid;
        margin: 0.3em 0;
        padding-left: 1.5em;
      }
      .content-text {
        max-height: none !important;
        overflow-y: visible !important;
        height: auto !important;
      }
      .meta-info {
        page-break-after: avoid;
        margin-bottom: 0.5em !important;
        padding: 10px !important;
      }
      .meta-item {
        margin-bottom: 0.3em !important;
      }
      blockquote {
        margin: 0.4em 0;
        padding-left: 1em;
        border-left: 3px solid #ddd;
      }
      code {
        padding: 0.1em 0.3em;
        background: #f5f5f5;
        border-radius: 3px;
      }
      pre {
        margin: 0.4em 0;
        padding: 0.5em;
        background: #f5f5f5;
        border-radius: 4px;
        overflow-x: auto;
      }
      hr {
        margin: 0.5em 0;
        border: none;
        border-top: 1px solid #ddd;
      }
    `;
    element.insertBefore(style, element.firstChild);

    const loadingMsg = document.createElement("div");
    loadingMsg.textContent = "正在生成PDF，请稍候...";
    loadingMsg.style.cssText =
      "position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.8); color: white; padding: 20px 40px; border-radius: 8px; z-index: 9999; font-size: 16px;";
    document.body.appendChild(loadingMsg);

    html2pdf()
      .set(opt)
      .from(element)
      .save()
      .then(() => {
        document.body.removeChild(loadingMsg);
        alert("PDF导出成功！");
      })
      .catch((err) => {
        console.error("PDF导出失败:", err);
        document.body.removeChild(loadingMsg);
        alert("PDF导出失败，请重试");
      });
  };

  const getVideoReportContent = () => {
    if (!videoResult) return "";
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
    return reportContent;
  };

  const getImageReportContent = () => {
    if (!result?.ai_report) return "";
    return typeof result.ai_report === "string"
      ? result.ai_report
      : JSON.stringify(result.ai_report, null, 2);
  };

  const handleDownloadVideoReport = () => {
    downloadMarkdown(
      getVideoReportContent(),
      `video_analysis_${videoResult.analysis_id}.md`,
      "暂无报告内容可下载",
    );
  };

  const handleDownloadImageReport = () => {
    downloadMarkdown(
      getImageReportContent(),
      `image_analysis_${result.analysis_id}.md`,
      "暂无图像分析报告可下载",
    );
  };

  const handleExportVideoPDF = () => {
    exportElementToPdf(
      videoReportContentRef,
      `视频分析报告_${videoResult.analysis_id}`,
      "暂无报告内容可导出",
    );
  };

  const handleExportImagePDF = () => {
    exportElementToPdf(
      imageReportContentRef,
      `图像分析报告_${result.analysis_id}`,
      "暂无图像分析报告可导出",
    );
  };

  // ============ 图像分析处理函数 ============
  const handleImageFile = (file) => {
    if (!file) return;
    setAnalysisForm({ ...analysisForm, imageFile: file });
    setUploadedImageId(null);
    setUploadInfo(null);
    setUploadToast(null);
    setResult(null);
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
      setUploadInfo(data);
      setUploadToast(null);
      setResult(null);
    } catch (err) {
      setUploadInfo(null);
      setError(null);
      setUploadToast({
        type: "error",
        message: err.message || "图像上传失败",
      });
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

    const reportContent = getImageReportContent();
    const formattedTime = formatDateTime(result.analyzed_at);
    const imageMetadata = result.details?.image_metadata || null;
    const visualMetrics = result.details?.visual_metrics || null;
    const aiDetails = result.details?.ai_result || {};
    const eyeEvidence = Array.isArray(aiDetails.eye_evidence)
      ? aiDetails.eye_evidence
      : [];
    const analysisHighlights = Array.isArray(aiDetails.analysis_highlights)
      ? aiDetails.analysis_highlights
      : [];
    const analysisLimitations = Array.isArray(aiDetails.analysis_limitations)
      ? aiDetails.analysis_limitations
      : [];

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
          <h3>🖼️ 图像分析报告</h3>
          <div style={{ display: "flex", gap: "10px" }}>
            {reportContent && (
              <>
                <button
                  className="btn"
                  onClick={handleDownloadImageReport}
                  style={{ padding: "8px 15px", fontSize: "14px" }}
                >
                  📥 下载Markdown
                </button>
                <button
                  className="btn"
                  onClick={handleExportImagePDF}
                  style={{
                    padding: "8px 15px",
                    fontSize: "14px",
                    background:
                      "linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)",
                  }}
                >
                  📄 导出PDF
                </button>
              </>
            )}
          </div>
        </div>

        <div ref={imageReportContentRef}>
          <div
            className="meta-info"
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
            <div className="meta-item">
              <span style={{ fontWeight: 600, color: "#666" }}>🆔 分析ID:</span>
              <span style={{ marginLeft: "8px" }}>{result.analysis_id}</span>
            </div>
            <div className="meta-item">
              <span style={{ fontWeight: 600, color: "#666" }}>🖼️ 图像ID:</span>
              <span style={{ marginLeft: "8px" }}>{result.image_id}</span>
            </div>
            <div className="meta-item">
              <span style={{ fontWeight: 600, color: "#666" }}>📊 分析类型:</span>
              <span style={{ marginLeft: "8px" }}>
                {result.analysis_type === "hybrid_ai" && "Few-shot 混合分析"}
                {result.analysis_type === "fusion" && "融合分析"}
                {result.analysis_type === "opencv" && "OpenCV 分析"}
              </span>
            </div>
            <div className="meta-item">
              <span style={{ fontWeight: 600, color: "#666" }}>🧠 分析方法:</span>
              <span style={{ marginLeft: "8px" }}>{result.method}</span>
            </div>
            <div className="meta-item">
              <span style={{ fontWeight: 600, color: "#666" }}>📈 综合置信度:</span>
              <span
                style={{
                  marginLeft: "8px",
                  fontWeight: "bold",
                  color:
                    result.confidence >= 0.8
                      ? "#10b981"
                      : result.confidence >= 0.6
                        ? "#f59e0b"
                        : "#ef4444",
                }}
              >
                {(result.confidence * 100).toFixed(1)}%
              </span>
            </div>
            {typeof result.consistency_score === "number" && (
              <div className="meta-item">
                <span style={{ fontWeight: 600, color: "#666" }}>
                  🔍 一致性评分:
                </span>
                <span style={{ marginLeft: "8px", fontWeight: "bold" }}>
                  {(result.consistency_score * 100).toFixed(1)}%
                </span>
              </div>
            )}
            {result.processing_time && (
              <div className="meta-item">
                <span style={{ fontWeight: 600, color: "#666" }}>
                  ⏱️ 处理时间:
                </span>
                <span style={{ marginLeft: "8px" }}>
                  {result.processing_time.toFixed(2)}秒
                </span>
              </div>
            )}
            {formattedTime && (
              <div className="meta-item">
                <span style={{ fontWeight: 600, color: "#666" }}>
                  🕐 分析时间:
                </span>
                <span style={{ marginLeft: "8px" }}>{formattedTime}</span>
              </div>
            )}
            {result.model_used && (
              <div className="meta-item">
                <span style={{ fontWeight: 600, color: "#666" }}>🤖 视觉模型:</span>
                <span style={{ marginLeft: "8px" }}>{result.model_used}</span>
              </div>
            )}
            {imageMetadata?.filename && (
              <div className="meta-item">
                <span style={{ fontWeight: 600, color: "#666" }}>🖼 文件名:</span>
                <span style={{ marginLeft: "8px" }}>{imageMetadata.filename}</span>
              </div>
            )}
            {imageMetadata?.width && imageMetadata?.height && (
              <div className="meta-item">
                <span style={{ fontWeight: 600, color: "#666" }}>📐 分辨率:</span>
                <span style={{ marginLeft: "8px" }}>
                  {imageMetadata.width} × {imageMetadata.height}
                </span>
              </div>
            )}
            {result.fewshot_examples_used?.length > 0 && (
              <div className="meta-item">
                <span style={{ fontWeight: 600, color: "#666" }}>
                  🧪 Few-shot 样例:
                </span>
                <span style={{ marginLeft: "8px" }}>
                  {result.fewshot_examples_used.join(", ")}
                </span>
              </div>
            )}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
              gap: "15px",
              marginBottom: "20px",
            }}
          >
            {result.center && (
              <div
                style={{
                  background: "#f9fafb",
                  padding: "15px",
                  borderRadius: "8px",
                }}
              >
                <h5 style={{ marginBottom: "10px" }}>台风中心位置</h5>
                <p>
                  <strong>坐标:</strong> ({result.center.pixel_x?.toFixed(1)},{" "}
                  {result.center.pixel_y?.toFixed(1)}) 像素
                </p>
                <p>
                  <strong>置信度:</strong>{" "}
                  {(result.center.confidence * 100).toFixed(1)}%
                </p>
              </div>
            )}

            {result.intensity && (
              <div
                style={{
                  background: "#f9fafb",
                  padding: "15px",
                  borderRadius: "8px",
                }}
              >
                <h5 style={{ marginBottom: "10px" }}>强度评估</h5>
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
            )}

            {result.eye && (
              <div
                style={{
                  background: "#f9fafb",
                  padding: "15px",
                  borderRadius: "8px",
                }}
              >
                <h5 style={{ marginBottom: "10px" }}>台风眼检测</h5>
                <p>
                  <strong>检测结果:</strong>{" "}
                  {result.eye.detected ? "检测到台风眼" : "未检测到台风眼"}
                </p>
                {result.eye.diameter_km && (
                  <p>
                    <strong>估计直径:</strong> {result.eye.diameter_km.toFixed(1)} km
                  </p>
                )}
                <p>
                  <strong>置信度:</strong>{" "}
                  {(result.eye.confidence * 100).toFixed(1)}%
                </p>
              </div>
            )}

            {result.structure && (
              <div
                style={{
                  background: "#f9fafb",
                  padding: "15px",
                  borderRadius: "8px",
                }}
              >
                <h5 style={{ marginBottom: "10px" }}>结构特征</h5>
                <p>
                  <strong>螺旋评分:</strong>{" "}
                  {(result.structure.spiral_score * 100).toFixed(1)}%
                </p>
                {result.structure.organization && (
                  <p>
                    <strong>组织程度:</strong> {result.structure.organization}
                  </p>
                )}
              </div>
            )}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "15px",
              marginBottom: "20px",
            }}
          >
            {imageMetadata && (
              <div
                style={{
                  background: "#f9fafb",
                  padding: "15px",
                  borderRadius: "8px",
                }}
              >
                <h5 style={{ marginBottom: "10px" }}>图片基础信息</h5>
                <p>
                  <strong>格式:</strong> {imageMetadata.format || "未知"}
                </p>
                <p>
                  <strong>色彩模式:</strong> {imageMetadata.mode || "未知"}
                </p>
                <p>
                  <strong>通道:</strong>{" "}
                  {Array.isArray(imageMetadata.bands)
                    ? imageMetadata.bands.join(", ")
                    : "未知"}
                </p>
                {imageMetadata.file_size ? (
                  <p>
                    <strong>文件大小:</strong>{" "}
                    {formatFileSize(imageMetadata.file_size)}
                  </p>
                ) : null}
              </div>
            )}

            {visualMetrics && (
              <div
                style={{
                  background: "#f9fafb",
                  padding: "15px",
                  borderRadius: "8px",
                }}
              >
                <h5 style={{ marginBottom: "10px" }}>视觉统计特征</h5>
                <p>
                  <strong>亮度均值:</strong>{" "}
                  {typeof visualMetrics.brightness === "number"
                    ? visualMetrics.brightness.toFixed(1)
                    : "暂无"}
                </p>
                <p>
                  <strong>对比度:</strong>{" "}
                  {typeof visualMetrics.contrast === "number"
                    ? visualMetrics.contrast.toFixed(1)
                    : "暂无"}
                </p>
                <p>
                  <strong>清晰度:</strong>{" "}
                  {typeof visualMetrics.sharpness === "number"
                    ? visualMetrics.sharpness.toFixed(1)
                    : "暂无"}
                </p>
                <p>
                  <strong>云量覆盖估计:</strong>{" "}
                  {formatPercentage(visualMetrics.cloud_coverage)}
                </p>
              </div>
            )}

            {(aiDetails.eye_position_description ||
              aiDetails.center_location_hint ||
              aiDetails.overall_assessment) && (
              <div
                style={{
                  background: "#f9fafb",
                  padding: "15px",
                  borderRadius: "8px",
                }}
              >
                <h5 style={{ marginBottom: "10px" }}>AI 眼区判读</h5>
                <p>
                  <strong>综合判断:</strong>{" "}
                  {aiDetails.overall_assessment || "未提供"}
                </p>
                <p>
                  <strong>眼区位置:</strong>{" "}
                  {aiDetails.eye_position_description || "未提供"}
                </p>
                <p>
                  <strong>相对方位:</strong>{" "}
                  {aiDetails.center_location_hint || "未提供"}
                </p>
                <p>
                  <strong>AI 置信度:</strong>{" "}
                  {formatPercentage(aiDetails.eye_confidence)}
                </p>
              </div>
            )}

            {(aiDetails.intensity_assessment ||
              aiDetails.organization_assessment ||
              aiDetails.development_stage ||
              aiDetails.cloud_system_description) && (
              <div
                style={{
                  background: "#f9fafb",
                  padding: "15px",
                  borderRadius: "8px",
                }}
              >
                <h5 style={{ marginBottom: "10px" }}>AI 结构解读</h5>
                <p>
                  <strong>强度解读:</strong>{" "}
                  {aiDetails.intensity_assessment || "未提供"}
                </p>
                <p>
                  <strong>组织程度:</strong>{" "}
                  {aiDetails.organization_assessment || "未提供"}
                </p>
                <p>
                  <strong>发展阶段:</strong>{" "}
                  {aiDetails.development_stage || "未提供"}
                </p>
                <p>
                  <strong>云系结构:</strong>{" "}
                  {aiDetails.cloud_system_description || "未提供"}
                </p>
              </div>
            )}
          </div>

          {(eyeEvidence.length > 0 ||
            analysisHighlights.length > 0 ||
            analysisLimitations.length > 0) && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                gap: "15px",
                marginBottom: "20px",
              }}
            >
              {eyeEvidence.length > 0 && (
                <div
                  style={{
                    padding: "15px",
                    background: "#eff6ff",
                    borderRadius: "8px",
                    border: "1px solid #bfdbfe",
                  }}
                >
                  <h4 style={{ marginBottom: "8px" }}>台风眼判读依据</h4>
                  <ul style={{ margin: 0, paddingLeft: "20px" }}>
                    {eyeEvidence.map((item, index) => (
                      <li key={`${item}-${index}`}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}

              {analysisHighlights.length > 0 && (
                <div
                  style={{
                    padding: "15px",
                    background: "#ecfdf5",
                    borderRadius: "8px",
                    border: "1px solid #a7f3d0",
                  }}
                >
                  <h4 style={{ marginBottom: "8px" }}>关键发现</h4>
                  <ul style={{ margin: 0, paddingLeft: "20px" }}>
                    {analysisHighlights.map((item, index) => (
                      <li key={`${item}-${index}`}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}

              {analysisLimitations.length > 0 && (
                <div
                  style={{
                    padding: "15px",
                    background: "#fff7ed",
                    borderRadius: "8px",
                    border: "1px solid #fdba74",
                  }}
                >
                  <h4 style={{ marginBottom: "8px" }}>分析局限</h4>
                  <ul style={{ margin: 0, paddingLeft: "20px" }}>
                    {analysisLimitations.map((item, index) => (
                      <li key={`${item}-${index}`}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {result.summary && (
            <div
              style={{
                padding: "15px",
                background: "#eff6ff",
                borderRadius: "8px",
                marginBottom: "20px",
                border: "1px solid #bfdbfe",
              }}
            >
              <h4 style={{ marginBottom: "8px" }}>AI 摘要</h4>
              <p style={{ margin: 0 }}>{result.summary}</p>
            </div>
          )}

          {result.risk_flags?.length > 0 && (
            <div
              style={{
                padding: "15px",
                background: "#fef3c7",
                borderRadius: "8px",
                color: "#92400e",
                marginBottom: "20px",
              }}
            >
              <h4 style={{ marginBottom: "8px" }}>风险提示</h4>
              <ul style={{ margin: 0, paddingLeft: "20px" }}>
                {result.risk_flags.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            </div>
          )}

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
              <p>暂无图像分析报告内容</p>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderVideoResult = () => {
    if (!videoResult) return null;

    const reportContent = getVideoReportContent();
    const formattedTime = formatDateTime(videoResult.created_at);

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
              <>
                <button
                  className="btn"
                  onClick={handleDownloadVideoReport}
                  style={{ padding: "8px 15px", fontSize: "14px" }}
                >
                  📥 下载Markdown
                </button>
                <button
                  className="btn"
                  onClick={handleExportVideoPDF}
                  style={{
                    padding: "8px 15px",
                    fontSize: "14px",
                    background:
                      "linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)",
                  }}
                >
                  📄 导出PDF
                </button>
              </>
            )}
          </div>
        </div>

        {/* 报告内容容器 - 添加ref用于PDF导出 */}
        <div ref={videoReportContentRef}>
          <div
            className="meta-info"
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
            <div className="meta-item">
              <span style={{ fontWeight: 600, color: "#666" }}>🆔 分析ID:</span>
              <span style={{ marginLeft: "8px" }}>
                {videoResult.analysis_id}
              </span>
            </div>
            <div className="meta-item">
              <span style={{ fontWeight: 600, color: "#666" }}>
                📊 分析类型:
              </span>
              <span style={{ marginLeft: "8px" }}>
                {videoResult.analysis_type === "comprehensive" && "综合分析"}
                {videoResult.analysis_type === "tracking" && "台风追踪"}
                {videoResult.analysis_type === "intensity" && "强度评估"}
                {videoResult.analysis_type === "structure" && "结构分析"}
              </span>
            </div>
            <div className="meta-item">
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
              <div className="meta-item">
                <span style={{ fontWeight: 600, color: "#666" }}>
                  ⏱️ 处理时间:
                </span>
                <span style={{ marginLeft: "8px" }}>
                  {videoResult.processing_time.toFixed(2)}秒
                </span>
              </div>
            )}
            {formattedTime && (
              <div className="meta-item">
                <span style={{ fontWeight: 600, color: "#666" }}>
                  🕐 分析时间:
                </span>
                <span style={{ marginLeft: "8px" }}>{formattedTime}</span>
              </div>
            )}
            {videoResult.frame_count > 0 && (
              <div className="meta-item">
                <span style={{ fontWeight: 600, color: "#666" }}>
                  🎞️ 分析帧数:
                </span>
                <span style={{ marginLeft: "8px" }}>
                  {videoResult.frame_count} 帧
                </span>
              </div>
            )}
            {videoResult.user_id && (
              <div className="meta-item">
                <span style={{ fontWeight: 600, color: "#666" }}>
                  👤 用户ID:
                </span>
                <span style={{ marginLeft: "8px" }}>{videoResult.user_id}</span>
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
            boxShadow:
              activeTab === "image" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
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
            boxShadow:
              activeTab === "video" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
            transition: "all 0.2s",
          }}
        >
          🎬 视频分析
        </button>
      </div>

      {activeTab === "image" && (
        <div className="image-upload-stage">
          {uploadToast && (
            <div className={`upload-toast upload-toast-${uploadToast.type}`}>
              <span>{uploadToast.message}</span>
              <button
                type="button"
                className="upload-toast-close"
                onClick={() => setUploadToast(null)}
                aria-label="关闭提示"
              >
                ×
              </button>
            </div>
          )}

          <h3 style={{ marginBottom: "20px" }}>卫星云图分析</h3>

          <div className="form-group">
            <label
              style={{ fontWeight: 600, marginBottom: "8px", display: "block" }}
            >
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
            <label
              style={{ fontWeight: 600, marginBottom: "8px", display: "block" }}
            >
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
                  <div style={{ fontSize: "40px", marginBottom: "12px" }}>
                    📄
                  </div>
                  <p style={{ fontWeight: 600, marginBottom: "4px" }}>
                    {analysisForm.imageFile.name}
                  </p>
                  <p style={{ fontSize: "13px", color: "#6b7280" }}>
                    {formatFileSize(analysisForm.imageFile.size)}
                  </p>
                  <p
                    style={{
                      fontSize: "13px",
                      color: "#3b82f6",
                      marginTop: "8px",
                    }}
                  >
                    点击或拖放更换文件
                  </p>
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: "40px", marginBottom: "12px" }}>
                    🖼️
                  </div>
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

          {uploadedImageId && uploadInfo && (
            <>
              <div
                className="info-card"
                style={{
                  marginBottom: "15px",
                  background: "#ecfdf5",
                  border: "1px solid #a7f3d0",
                  borderRadius: "8px",
                  textAlign: "center",
                }}
              >
                <p style={{ margin: 0, color: "#10b981", fontWeight: 600 }}>
                  ✅ 图像已上传，ID: {uploadedImageId}
                </p>
                <div
                  style={{
                    marginTop: "8px",
                    display: "flex",
                    justifyContent: "center",
                    flexWrap: "wrap",
                    gap: "12px",
                    fontSize: "13px",
                    color: "#065f46",
                  }}
                >
                  <span>{uploadInfo.filename}</span>
                  {uploadInfo.width && uploadInfo.height ? (
                    <span>
                      {uploadInfo.width} × {uploadInfo.height}
                    </span>
                  ) : null}
                  {uploadInfo.format ? <span>{uploadInfo.format}</span> : null}
                  {uploadInfo.size ? (
                    <span>{formatFileSize(uploadInfo.size)}</span>
                  ) : null}
                </div>
              </div>

              {uploadPreviewUrl && (
                <div className="image-preview">
                  <div
                    className="image-preview-title"
                    style={{ textAlign: "center" }}
                  >
                    上传图片预览
                  </div>
                  <div className="image-preview-wrapper">
                    <img
                      className="image-preview-img"
                      src={uploadPreviewUrl}
                      alt={uploadInfo.filename || "上传图片预览"}
                    />
                  </div>
                </div>
              )}
            </>
          )}

          <div className="form-group">
            <label
              style={{ fontWeight: 600, marginBottom: "8px", display: "block" }}
            >
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
              <option value="hybrid_ai">Few-shot 混合分析（推荐）</option>
              <option value="fusion">融合结构化分析</option>
              <option value="opencv">OpenCV传统方法</option>
            </select>
          </div>

          <div className="form-group">
            <label
              style={{ fontWeight: 600, marginBottom: "8px", display: "block" }}
            >
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
              <option value="visible">可见光卫星云图（支持样例增强）</option>
              <option value="infrared">红外卫星云图</option>
            </select>
          </div>

          <button
            className="btn"
            onClick={handleAnalysis}
            disabled={loading || !uploadedImageId}
            style={{
              width: "100%",
              padding: "14px 20px",
              fontSize: "15px",
              fontWeight: 600,
            }}
          >
            {loading ? "分析中..." : "开始分析"}
          </button>

          {error && (
            <div
              className="error-message"
              style={{ marginTop: "20px", borderRadius: "8px" }}
            >
              {error}
            </div>
          )}

          {loading && (
            <div className="loading" style={{ borderRadius: "8px" }}>
              处理中...
            </div>
          )}

          {renderImageResult()}
        </div>
      )}

      {activeTab === "video" && (
        <div>
          <h3 style={{ marginBottom: "20px" }}>视频内容分析</h3>

          <div className="form-group">
            <label
              style={{ fontWeight: 600, marginBottom: "8px", display: "block" }}
            >
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
                background: isAnalyzing
                  ? "#f3f4f6"
                  : videoDragOver
                    ? "#eff6ff"
                    : "#fafafa",
                textAlign: "center",
                cursor: isAnalyzing ? "not-allowed" : "pointer",
                transition: "all 0.2s",
                opacity: isAnalyzing ? 0.6 : 1,
              }}
            >
              {videoFile ? (
                <div>
                  <div style={{ fontSize: "40px", marginBottom: "12px" }}>
                    🎬
                  </div>
                  <p style={{ fontWeight: 600, marginBottom: "4px" }}>
                    {videoFile.name}
                  </p>
                  <p style={{ fontSize: "13px", color: "#6b7280" }}>
                    {formatFileSize(videoFile.size)}
                  </p>
                  {!isAnalyzing && (
                    <p
                      style={{
                        fontSize: "13px",
                        color: "#3b82f6",
                        marginTop: "8px",
                      }}
                    >
                      点击或拖放更换文件
                    </p>
                  )}
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: "40px", marginBottom: "12px" }}>
                    📁
                  </div>
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
            <div
              className="error-message"
              style={{ marginBottom: "15px", borderRadius: "8px" }}
            >
              {videoError}
            </div>
          )}

          <div className="form-group">
            <label
              style={{ fontWeight: 600, marginBottom: "8px", display: "block" }}
            >
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
              <label
                style={{
                  fontWeight: 600,
                  marginBottom: "8px",
                  display: "block",
                }}
              >
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
            <div
              className="loading"
              style={{ marginTop: "20px", borderRadius: "8px" }}
            >
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
