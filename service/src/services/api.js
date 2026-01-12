/**
 * API服务层 - 封装所有后端API调用
 */
import axios from "axios";

// API基础URL
const API_BASE_URL = "http://localhost:8000/api";

// 创建axios实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    console.log(`🚀 API请求: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error("❌ 请求错误:", error);
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    console.log(`✅ API响应: ${response.config.url}`, response.data);
    return response.data;
  },
  (error) => {
    console.error("❌ 响应错误:", error);

    // 改进错误信息提取逻辑
    let message = "请求失败";

    if (error.response) {
      // 服务器返回了错误响应
      const data = error.response.data;
      if (typeof data === "string") {
        message = data;
      } else if (data && typeof data.detail === "string") {
        message = data.detail;
      } else if (data && typeof data.message === "string") {
        message = data.message;
      } else {
        message = `请求失败: ${error.response.status} ${error.response.statusText}`;
      }
    } else if (error.request) {
      // 请求已发送但没有收到响应
      message = "无法连接到服务器，请检查后端服务是否正常运行";
    } else if (error.message) {
      // 请求配置出错
      message = error.message;
    }

    console.error("❌ 错误信息:", message);
    return Promise.reject(new Error(message));
  }
);

// ========== 台风数据API ==========

/**
 * 获取台风列表
 * @param {Object} params - 查询参数
 * @param {number} params.year - 年份筛选
 * @param {number} params.status - 状态筛选（0=已停止, 1=活跃）
 * @param {number} params.limit - 返回数量限制
 */
export const getTyphoonList = async (params = {}) => {
  return apiClient.get("/typhoons", { params });
};

/**
 * 根据ID获取台风详情
 */
export const getTyphoonById = async (typhoonId) => {
  return apiClient.get(`/typhoons/${typhoonId}`);
};

/**
 * 获取台风路径数据
 */
export const getTyphoonPath = async (typhoonId) => {
  return apiClient.get(`/typhoons/${typhoonId}/path`);
};

/**
 * 搜索台风
 */
export const searchTyphoons = async (params) => {
  return apiClient.get("/typhoons/search", { params });
};

// ========== 统计分析API ==========

/**
 * 获取年度统计
 */
export const getYearlyStatistics = async (startYear, endYear) => {
  return apiClient.get("/statistics/yearly", {
    params: { start_year: startYear, end_year: endYear },
  });
};

/**
 * 获取强度分布统计
 */
export const getIntensityStatistics = async (year, typhoonId) => {
  const params = {};
  if (year) params.year = year;
  if (typhoonId) params.typhoon_id = typhoonId;
  return apiClient.get("/statistics/intensity", { params });
};

/**
 * 台风对比分析
 */
export const compareTyphoons = async (typhoonIds) => {
  return apiClient.post("/statistics/comparison", {
    typhoon_ids: typhoonIds,
  });
};

// ========== 预警中心API ==========

/**
 * 获取活跃预警
 */
export const getActiveAlerts = async () => {
  return apiClient.get("/alert/active");
};

/**
 * 获取历史预警
 */
export const getAlertHistory = async (typhoonId, level, limit = 20) => {
  const params = { limit };
  if (typhoonId) params.typhoon_id = typhoonId;
  if (level) params.alert_level = level;
  return apiClient.get("/alert/history", { params });
};

/**
 * 获取预警规则
 */
export const getAlertRules = async () => {
  return apiClient.get("/alert/rules");
};

/**
 * 创建预警规则
 */
export const createAlertRule = async (ruleData) => {
  return apiClient.post("/alert/rules", ruleData);
};

// ========== 数据导出API ==========

/**
 * 导出单个台风数据
 */
export const exportTyphoon = async (
  typhoonId,
  format = "csv",
  includePath = true
) => {
  const url = `${API_BASE_URL}/export/typhoon/${typhoonId}?format=${format}&include_path=${includePath}`;
  window.open(url, "_blank");
};

/**
 * 批量导出台风数据
 */
export const exportBatchTyphoons = async (
  typhoonIds,
  format = "csv",
  includePath = true
) => {
  try {
    const response = await fetch(`${API_BASE_URL}/export/batch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        typhoon_ids: typhoonIds,
        format: format,
        include_path: includePath,
      }),
    });

    if (!response.ok) {
      throw new Error(`导出失败: ${response.statusText}`);
    }

    // 获取文件名
    const contentDisposition = response.headers.get("Content-Disposition");
    let filename = `typhoons_batch_${
      new Date().toISOString().split("T")[0]
    }.${format}`;
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename=(.+)/);
      if (filenameMatch) {
        filename = filenameMatch[1].replace(/['"]/g, "");
      }
    }

    // 下载文件
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(downloadUrl);

    return { success: true, count: typhoonIds.length };
  } catch (error) {
    throw new Error(`批量导出失败: ${error.message}`);
  }
};

// ========== 爬虫管理API ==========

/**
 * 获取爬虫状态
 */
export const getCrawlerStatus = async () => {
  return apiClient.get("/crawler/status");
};

/**
 * 获取爬虫日志
 */
export const getCrawlerLogs = async (limit = 100) => {
  return apiClient.get("/crawler/logs", { params: { limit } });
};

/**
 * 手动触发爬虫
 */
export const triggerCrawler = async () => {
  return apiClient.post("/crawler/trigger");
};

// ========== 智能预测API ==========

/**
 * 路径预测
 */
export const predictPath = async (typhoonId, hours) => {
  return apiClient.post("/prediction/path", {
    typhoon_id: typhoonId,
    hours: hours,
  });
};

/**
 * 强度预测
 */
export const predictIntensity = async (typhoonId, hours) => {
  return apiClient.post("/prediction/intensity", {
    typhoon_id: typhoonId,
    hours: hours,
  });
};

// ========== 图像分析API ==========

/**
 * 卫星云图分析
 */
export const analyzeSatelliteImage = async (typhoonId, imageUrl) => {
  return apiClient.post("/analysis/satellite", {
    typhoon_id: typhoonId,
    image_url: imageUrl,
  });
};

// ========== 报告生成API ==========

/**
 * 生成台风报告
 */
export const generateReport = async (
  typhoonId,
  reportType,
  aiProvider = "glm"
) => {
  return apiClient.post("/report/generate", {
    typhoon_id: typhoonId,
    report_type: reportType,
    ai_provider: aiProvider,
  });
};

/**
 * 下载报告
 */
export const downloadReport = async (reportId, format = "pdf") => {
  const url = `${API_BASE_URL}/report/download/${reportId}?format=${format}`;
  window.open(url, "_blank");
};

export default apiClient;
