/**
 * 报告生成组件
 */
import React, { useState, useRef } from "react";

import { marked } from "marked";

// 配置 marked 为同步模式
marked.setOptions({
  async: false,
});
import html2pdf from "html2pdf.js";
import { useSearchParams, useNavigate } from "react-router-dom";
import { message } from "antd";
import {
  getTyphoonList,
  getReportById,
  getTyphoonById,
  generateReport,
} from "../services/api";
import "../styles/ReportGeneration.css";
import "../styles/TyphoonQuery.css"; // 导入下拉选择器样式
import "../styles/common.css";

function ReportGeneration() {
  const [searchParams] = useSearchParams();
  const urlReportId = searchParams.get("report_id");
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // 追踪result变化
  React.useEffect(() => {
    console.log("result state changed:", result);
  }, [result]);

  // PDF导出引用
  const reportContentRef = useRef(null);

  // 使用ref跟踪是否已经处理过URL参数，避免重复处理
  const hasProcessedUrlReportId = useRef(false);

  // 报告生成表单
  const [reportForm, setReportForm] = useState({
    typhoonId: "",
    reportType: "comprehensive", // 修改默认值为comprehensive
    aiProvider: "deepseek",
  });

  // 下拉选择器状态
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [dropdownTyphoons, setDropdownTyphoons] = useState([]);
  const [dropdownLoading, setDropdownLoading] = useState(false);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [availableYears, setAvailableYears] = useState([]);
  const [displayText, setDisplayText] = useState(""); // 用于输入框显示的文本

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

  // 处理URL参数中的report_id - 自动加载报告详情
  React.useEffect(() => {
    if (urlReportId && !hasProcessedUrlReportId.current) {
      console.log(`📌 检测到URL参数中的report_id: ${urlReportId}`);

      // 验证report_id格式（必须是数字）
      if (
        !urlReportId ||
        urlReportId.trim() === "" ||
        isNaN(parseInt(urlReportId))
      ) {
        console.warn(`⚠️ 无效的报告ID: ${urlReportId}，跳过自动加载`);
        hasProcessedUrlReportId.current = true;
        return;
      }

      // 获取报告详情
      const loadReportAndDisplay = async () => {
        try {
          console.log(`📡 获取报告详情: ${urlReportId}`);
          const reportData = await getReportById(urlReportId);

          console.log(`✅ 报告详情数据加载成功:`, reportData);

          // 填充表单
          const typhoonId = reportData.typhoon_id || "";
          const reportType = reportData.report_type || "comprehensive";
          const aiProvider =
            reportData.ai_provider || reportData.model_used || "deepseek";

          setReportForm({
            typhoonId: typhoonId,
            reportType: reportType,
            aiProvider: aiProvider,
          });

          // 获取台风详情以获取英文名和中文名
          let typhoonNameEn = "暂无";
          let typhoonNameCn = "";

          if (typhoonId) {
            try {
              console.log(`📡 获取台风详情: ${typhoonId}`);
              const typhoonData = await getTyphoonById(typhoonId);
              console.log(`✅ 台风详情数据加载成功:`, typhoonData);

              typhoonNameEn = typhoonData.typhoon_name || "暂无";
              typhoonNameCn = typhoonData.typhoon_name_cn || "";
            } catch (err) {
              console.error(`❌ 获取台风详情失败:`, err);
              // 如果获取台风详情失败，使用报告中的名称
              typhoonNameEn = reportData.typhoon_name || "暂无";
              typhoonNameCn = reportData.typhoon_name_cn || "";
            }
          }

          // 构建组合格式的显示文本：台风ID - 英文名 - 中文名
          const displayName = `${typhoonId} - ${typhoonNameEn}${
            typhoonNameCn ? ` - ${typhoonNameCn}` : ""
          }`;
          setDisplayText(displayName);
          console.log(`✅ 构建显示文本: ${displayName}`);

          // 设置查询结果
          setResult(reportData);

          // 从typhoon_id中提取年份并切换
          if (typhoonId) {
            const typhoonIdStr = String(typhoonId);
            if (typhoonIdStr.length >= 2) {
              const yearPrefix = typhoonIdStr.substring(0, 2);
              const targetYear = parseInt("20" + yearPrefix);

              if (
                !isNaN(targetYear) &&
                targetYear >= 2000 &&
                targetYear <= 2099
              ) {
                console.log(`📅 从typhoon_id提取年份: ${targetYear}`);
                setSelectedYear(targetYear);
              }
            }
          }

          hasProcessedUrlReportId.current = true;
        } catch (err) {
          console.error(`❌ 获取报告详情失败:`, err);
          setError(
            err.response?.data?.detail || err.message || "获取报告详情失败"
          );
          hasProcessedUrlReportId.current = true;
        }
      };

      loadReportAndDisplay();
    }
  }, [urlReportId]);

  // 当选择年份改变时，加载对应年份的台风列表
  React.useEffect(() => {
    if (dropdownOpen) {
      loadDropdownTyphoons(selectedYear);
    }
  }, [selectedYear, dropdownOpen]);

  // 当URL参数变化时，重置处理标志
  React.useEffect(() => {
    hasProcessedUrlReportId.current = false;
  }, [urlReportId]);

  // 处理输入框点击，打开下拉选择器
  const handleInputFocus = () => {
    setDropdownOpen(true);
    if (dropdownTyphoons.length === 0) {
      loadDropdownTyphoons(selectedYear);
    }
  };

  // 处理台风卡片点击
  const handleTyphoonCardClick = (typhoon) => {
    // 只存储台风ID用于查询
    setReportForm({ ...reportForm, typhoonId: typhoon.typhoon_id });

    // 构建显示文本：台风ID - 英文名 - 中文名
    const displayName = `${typhoon.typhoon_id} - ${typhoon.typhoon_name}${
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

  // 处理报告生成
  const handleGenerateReport = async () => {
    if (!reportForm.typhoonId) {
      alert("请输入台风ID");
      return;
    }

    const token = localStorage.getItem("token");
    if (!token) {
      message.warning("请先登录后再生成报告");
      navigate("/login");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const response = await generateReport(
        reportForm.typhoonId,
        reportForm.reportType,
        reportForm.aiProvider
      );
      // apiClient 的响应拦截器已经返回了 response.data
      console.log("报告生成成功，响应数据:", response);
      setResult(response);
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

    console.log("renderResult - result:", result);
    console.log("renderResult - report_content:", result.report_content);
    console.log("renderResult - content:", result.content);

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

      <div className="form-group typhoon-dropdown-container">
        <label>台风ID</label>
        <input
          type="text"
          placeholder="点击选择台风或输入台风ID"
          value={displayText || reportForm.typhoonId}
          onChange={(e) => {
            const value = e.target.value;
            // 用户手动输入时，清空displayText，只保留typhoonId
            setDisplayText("");
            setReportForm({ ...reportForm, typhoonId: value });
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
          <option value="prediction">预测分析报告</option>
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
          <option value="deepseek">DeepSeek</option>
          <option value="glm">智谱GLM (GLM-4.7)</option>
          <option value="qwen">通义千问 (Qwen)</option>
        </select>
        <small style={{ color: "#6b7280", display: "block", marginTop: "5px" }}>
          💡 提示：通义千问、DeepSeek和GLM均支持中文报告生成
        </small>
      </div>

      <button className="btn" onClick={handleGenerateReport} disabled={loading}>
        📝 生成报告
      </button>

      <div className="info-card" style={{ marginTop: "15px" }}>
        <p style={{ margin: 0, fontSize: "15px", color: "#1e40af" }}>
          💡 <strong>报告类型说明：</strong>
        </p>
        <ul
          style={{ margin: "8px 0 0 20px", fontSize: "14px", color: "#1e40af" }}
        >
          <li>
            <strong>综合分析报告：</strong>深入分析台风特征和发展过程
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
      {console.log(
        "JSX render - result:",
        result,
        "loading:",
        loading,
        "error:",
        error
      )}
      {result && <div key={result.id || Date.now()}>{renderResult()}</div>}
    </div>
  );
}

export default ReportGeneration;
