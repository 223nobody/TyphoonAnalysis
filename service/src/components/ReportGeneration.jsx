/**
 * 报告生成组件
 */
import React, { useState, useRef } from "react";
import axios from "axios";
import { marked } from "marked";
import html2pdf from "html2pdf.js";
import "../styles/ReportGeneration.css";
import "../styles/common.css";

function ReportGeneration() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // PDF导出引用
  const reportContentRef = useRef(null);

  // 报告生成表单
  const [reportForm, setReportForm] = useState({
    typhoonId: "",
    reportType: "comprehensive", // 修改默认值为comprehensive
    aiProvider: "glm",
  });

  // 处理报告生成
  const handleGenerateReport = async () => {
    if (!reportForm.typhoonId) {
      alert("请输入台风ID");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const response = await axios.post(`api/report/generate`, {
        typhoon_id: reportForm.typhoonId,
        report_type: reportForm.reportType,
        ai_provider: reportForm.aiProvider,
      });
      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "报告生成失败");
    } finally {
      setLoading(false);
    }
  };

  // 下载报告
  const handleDownloadReport = () => {
    // 参考index.html，使用report_content字段
    const reportContent = result.report_content || result.content;
    if (!reportContent) {
      alert("暂无报告内容可下载");
      return;
    }

    const blob = new Blob([reportContent], { type: "text/markdown" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    // 使用台风ID和报告类型生成文件名
    const typhoonId = result.typhoon_id || reportForm.typhoonId;
    a.download = `typhoon_${typhoonId}_${reportForm.reportType}_report.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  // 导出为PDF
  const handleExportPDF = () => {
    if (!reportContentRef.current) {
      alert("暂无报告内容可导出");
      return;
    }

    const typhoonId = result.typhoon_id || reportForm.typhoonId;
    const typhoonName = result.typhoon_name || "未命名";
    const reportType = reportForm.reportType;
    const timestamp = new Date().toISOString().slice(0, 10);

    // PDF配置选项
    const opt = {
      margin: [15, 15, 15, 15],
      filename: `台风${typhoonName}_${typhoonId}_${reportType}_${timestamp}.pdf`,
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

    // 克隆报告内容以避免修改原始DOM
    const element = reportContentRef.current.cloneNode(true);

    // 移除所有高度限制和滚动条，确保完整内容可见
    const contentSections = element.querySelectorAll(".content-text");
    contentSections.forEach((section) => {
      section.style.maxHeight = "none";
      section.style.overflowY = "visible";
      section.style.height = "auto";
    });

    // 添加PDF样式优化 - 紧凑格式
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

    // 显示加载提示
    const loadingMsg = document.createElement("div");
    loadingMsg.textContent = "正在生成PDF，请稍候...";
    loadingMsg.style.cssText =
      "position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.8); color: white; padding: 20px 40px; border-radius: 8px; z-index: 9999; font-size: 16px;";
    document.body.appendChild(loadingMsg);

    // 生成PDF
    html2pdf()
      .set(opt)
      .from(element)
      .save()
      .then(() => {
        console.log("PDF导出成功");
        document.body.removeChild(loadingMsg);
        alert("PDF导出成功！");
      })
      .catch((err) => {
        console.error("PDF导出失败:", err);
        document.body.removeChild(loadingMsg);
        alert("PDF导出失败，请重试");
      });
  };

  // 渲染报告结果 - 参考index.html的formatReportResult函数
  const renderResult = () => {
    if (!result) return null;

    // 参考index.html，使用report_content字段
    const reportContent = result.report_content || result.content || "";
    const typhoonId = result.typhoon_id || reportForm.typhoonId || "未知";
    const typhoonName = result.typhoon_name || "未命名";
    const modelUsed =
      result.model_used ||
      result.ai_provider ||
      reportForm.aiProvider ||
      "未知";
    const createdAt =
      result.created_at || result.generated_at || new Date().toISOString();

    // 格式化时间
    const formattedTime = new Date(createdAt).toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });

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
          <h3>📊 台风分析报告</h3>
          <div style={{ display: "flex", gap: "10px" }}>
            <button
              className="btn"
              onClick={handleDownloadReport}
              style={{ padding: "8px 15px", fontSize: "14px" }}
            >
              📥 下载Markdown
            </button>
            <button
              className="btn"
              onClick={handleExportPDF}
              style={{
                padding: "8px 15px",
                fontSize: "14px",
                background: "linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)",
              }}
            >
              📄 导出PDF
            </button>
          </div>
        </div>

        {/* 报告内容容器 - 添加ref用于PDF导出 */}
        <div ref={reportContentRef}>
          {/* 报告元数据 - 参考index.html的meta-info */}
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
              <span style={{ fontWeight: 600, color: "#666" }}>
                🆔 台风编号:
              </span>
              <span style={{ marginLeft: "8px" }}>{typhoonId}</span>
            </div>
            <div className="meta-item">
              <span style={{ fontWeight: 600, color: "#666" }}>
                🌀 台风名称:
              </span>
              <span style={{ marginLeft: "8px" }}>{typhoonName}</span>
            </div>
            <div className="meta-item">
              <span style={{ fontWeight: 600, color: "#666" }}>🤖 AI模型:</span>
              <span style={{ marginLeft: "8px" }}>{modelUsed}</span>
            </div>
            <div className="meta-item">
              <span style={{ fontWeight: 600, color: "#666" }}>
                ⏰ 生成时间:
              </span>
              <span style={{ marginLeft: "8px" }}>{formattedTime}</span>
            </div>
          </div>

          {/* 报告内容 - 参考index.html使用marked.parse */}
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
                dangerouslySetInnerHTML={{ __html: marked(reportContent) }}
              />
            </div>
          ) : (
            <div
              className="warning-card"
              style={{
                padding: "15px",
                background: "#fef3c7",
                borderRadius: "8px",
                color: "#f59e0b",
              }}
            >
              <h4>⚠️ 提示</h4>
              <p>报告内容为空，可能是生成过程中出现了问题。</p>
            </div>
          )}
        </div>
      </div>
    );
  };

  // 获取报告类型名称 - 更新为与index.html一致
  const getReportTypeName = (type) => {
    const names = {
      comprehensive: "综合分析报告",
      impact: "影响评估报告",
      prediction: "预测报告",
    };
    return names[type] || type;
  };

  return (
    <div>
      <h2>📊 报告生成</h2>

      <div className="form-group">
        <label>台风ID</label>
        <input
          type="text"
          placeholder="例如: 2501"
          value={reportForm.typhoonId}
          onChange={(e) =>
            setReportForm({ ...reportForm, typhoonId: e.target.value })
          }
        />
      </div>

      <div className="form-group">
        <label>报告类型</label>
        <select
          value={reportForm.reportType}
          onChange={(e) =>
            setReportForm({ ...reportForm, reportType: e.target.value })
          }
        >
          <option value="comprehensive">综合分析报告</option>
          <option value="impact">影响评估报告</option>
          <option value="prediction">预测报告</option>
        </select>
      </div>

      <div className="form-group">
        <label>AI模型选择</label>
        <select
          value={reportForm.aiProvider}
          onChange={(e) =>
            setReportForm({ ...reportForm, aiProvider: e.target.value })
          }
        >
          <option value="glm">智谱GLM (GLM-4.7)</option>
          <option value="qwen">通义千问 (Qwen)</option>
          <option value="deepseek">DeepSeek</option>
        </select>
        <small style={{ color: "#6b7280", display: "block", marginTop: "5px" }}>
          💡 提示：通义千问、DeepSeek和GLM均支持中文报告生成
        </small>
      </div>

      <button className="btn" onClick={handleGenerateReport} disabled={loading}>
        📝 生成报告
      </button>

      <div className="info-card" style={{ marginTop: "15px" }}>
        <p style={{ margin: 0, fontSize: "13px", color: "#1e40af" }}>
          💡 <strong>报告类型说明：</strong>
        </p>
        <ul
          style={{ margin: "8px 0 0 20px", fontSize: "12px", color: "#1e40af" }}
        >
          <li>
            <strong>台风概况报告：</strong>包含台风基本信息和路径概况
          </li>
          <li>
            <strong>详细分析报告：</strong>深入分析台风特征和发展过程
          </li>
          <li>
            <strong>影响评估报告：</strong>评估台风可能造成的影响
          </li>
          <li>
            <strong>预测分析报告：</strong>基于AI模型的预测分析
          </li>
        </ul>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="error-message" style={{ marginTop: "20px" }}>
          ❌ {error}
        </div>
      )}

      {/* 加载状态 */}
      {loading && (
        <div className="loading">
          <p>正在生成报告，请稍候...</p>
          <p style={{ fontSize: "12px", color: "#6b7280" }}>
            这可能需要几秒钟时间
          </p>
        </div>
      )}

      {/* 结果显示 */}
      {result && renderResult()}
    </div>
  );
}

export default ReportGeneration;
