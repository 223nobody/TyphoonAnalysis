/**
 * API服务层 - 封装所有后端API调用
 */
import axios from "axios";

// API基础URL
const API_BASE_URL = "/api";

/**
 * Header 导航接口路由配置
 * 仅配置接口路由路径，不包含样式和显示逻辑
 */
export const headerRoutes = {
  apiDocs: "/docs",
  apiHealth: "/health",
};

// 创建axios实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
});

//请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 添加认证令牌到请求头
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    // 改进错误信息提取逻辑
    let message = "请求失败";

    if (error.code === "ECONNABORTED" && error.message.includes("timeout")) {
      // 请求超时
      message = "请求超时，AI 服务响应时间过长，请稍后重试";
    } else if (error.response) {
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

    return Promise.reject(new Error(message));
  },
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
 * 根据ID获取报告详情
 */
export const getReportById = async (reportId) => {
  return apiClient.get(`/report/${reportId}`);
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
export const getAlertHistory = async (typhoonId, level, limit = 50) => {
  const params = { limit };
  if (typhoonId) params.typhoon_id = typhoonId;
  if (level) params.alert_level = level;
  return apiClient.get("/alert/history", { params });
};

/**
 * 获取台风预报路径数据（按预报机构分组）
 */
export const getTyphoonForecast = async (typhoonId) => {
  return apiClient.get(`/typhoons/${typhoonId}/forecast`);
};

// ========== 数据导出API ==========

/**
 * 导出单个台风数据
 */
export const exportTyphoon = async (
  typhoonId,
  format = "csv",
  includePath = true,
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
  includePath = true,
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
 * @param {string} typhoonId - 台风编号
 * @param {number} forecastHours - 预报时效（小时）
 * @param {boolean} useEnsemble - 是否使用集合预测
 */
export const predictPath = async (typhoonId, forecastHours, useEnsemble = false) => {
  return apiClient.post("/predictions/path", {
    typhoon_id: typhoonId,
    forecast_hours: forecastHours,
    use_ensemble: useEnsemble,
  });
};

/**
 * 强度预测
 * @param {string} typhoonId - 台风编号
 * @param {number} forecastHours - 预报时效（小时）
 */
export const predictIntensity = async (typhoonId, forecastHours) => {
  return apiClient.post("/predictions/intensity", {
    typhoon_id: typhoonId,
    forecast_hours: forecastHours,
  });
};

/**
 * 批量预测
 * @param {string[]} typhoonIds - 台风编号列表
 * @param {number} forecastHours - 预报时效（小时）
 */
export const predictBatch = async (typhoonIds, forecastHours) => {
  return apiClient.post("/predictions/batch", {
    typhoon_ids: typhoonIds,
    forecast_hours: forecastHours,
  });
};

/**
 * 获取台风预测记录
 * @param {string} typhoonId - 台风编号
 * @param {string} predictionType - 预测类型筛选(path/intensity)
 * @param {number} limit - 返回记录数量限制
 */
export const getTyphoonPredictions = async (typhoonId, predictionType = null, limit = 100) => {
  const params = { limit };
  if (predictionType) params.prediction_type = predictionType;
  return apiClient.get(`/predictions/${typhoonId}`, { params });
};

/**
 * 获取台风预测统计
 * @param {string} typhoonId - 台风编号
 */
export const getPredictionStats = async (typhoonId) => {
  return apiClient.get(`/predictions/stats/${typhoonId}`);
};

/**
 * 清除台风预测记录
 * @param {string} typhoonId - 台风编号
 */
export const clearPredictions = async (typhoonId) => {
  return apiClient.delete(`/predictions/${typhoonId}`);
};

/**
 * 任意起点预测
 * @param {string} typhoonId - 台风编号
 * @param {string} startTime - 起点时间（ISO格式）
 * @param {number} startLatitude - 起点纬度
 * @param {number} startLongitude - 起点经度
 * @param {number} startPressure - 起点中心气压（可选）
 * @param {number} startWindSpeed - 起点最大风速（可选）
 * @param {number} forecastHours - 预报时效（小时）
 */
export const predictFromArbitraryStart = async (
  typhoonId,
  startTime,
  startLatitude,
  startLongitude,
  startPressure = null,
  startWindSpeed = null,
  forecastHours = 48
) => {
  return apiClient.post("/predictions/arbitrary-start", {
    typhoon_id: typhoonId,
    start_time: startTime,
    start_latitude: startLatitude,
    start_longitude: startLongitude,
    start_pressure: startPressure,
    start_wind_speed: startWindSpeed,
    forecast_hours: forecastHours,
  });
};

/**
 * 滚动预测
 * @param {string} typhoonId - 台风编号
 * @param {number} initialForecastHours - 初始预报时效（小时）
 * @param {number} updateIntervalHours - 更新间隔（小时）
 * @param {number} maxIterations - 最大滚动次数
 * @param {number} confidenceThreshold - 置信度阈值
 */
export const rollingPrediction = async (
  typhoonId,
  initialForecastHours = 48,
  updateIntervalHours = 6,
  maxIterations = 5,
  confidenceThreshold = 0.5
) => {
  return apiClient.post("/predictions/rolling", {
    typhoon_id: typhoonId,
    initial_forecast_hours: initialForecastHours,
    update_interval_hours: updateIntervalHours,
    max_iterations: maxIterations,
    confidence_threshold: confidenceThreshold,
  });
};

/**
 * 虚拟观测点预测
 * @param {string} typhoonId - 台风编号
 * @param {Array} virtualObservations - 虚拟观测点列表
 * @param {number} forecastHours - 预报时效（小时）
 */
export const predictWithVirtualObservations = async (
  typhoonId,
  virtualObservations,
  forecastHours = 48
) => {
  return apiClient.post("/predictions/virtual-observations", {
    typhoon_id: typhoonId,
    virtual_observations: virtualObservations,
    forecast_hours: forecastHours,
  });
};

// ========== 图像分析API ==========

/**
 * 上传图像文件
 */
export const uploadImage = async (file, typhoonId = null) => {
  const formData = new FormData();
  formData.append("file", file);
  if (typhoonId) {
    formData.append("typhoon_id", typhoonId);
  }
  formData.append("image_type", "satellite");

  return apiClient.post("/images/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

/**
 * 分析图像（重构版本）
 * @param {number} imageId - 图像ID
 * @param {string} analysisType - 分析类型（basic/advanced/opencv/fusion）
 * @param {string} imageType - 图像类型（infrared/visible）
 */
export const analyzeImage = async (
  imageId,
  analysisType = "fusion",
  imageType = "infrared",
) => {
  return apiClient.post(
    `/images/analyze/${imageId}?analysis_type=${analysisType}&image_type=${imageType}`,
  );
};

/**
 * 获取台风的图像列表
 */
export const getTyphoonImages = async (
  typhoonId,
  imageType = null,
  limit = 20,
) => {
  const params = { limit };
  if (imageType) params.image_type = imageType;
  return apiClient.get(`/images/typhoon/${typhoonId}`, { params });
};

/**
 * 获取图像分析历史
 */
export const getImageAnalysisHistory = async (imageId) => {
  return apiClient.get(`/images/analysis/history/${imageId}`);
};

/**
 * 删除图像
 */
export const deleteImage = async (imageId) => {
  return apiClient.delete(`/images/${imageId}`);
};

/**
 * 卫星云图分析（旧版本，保持向后兼容）
 * @deprecated 请使用 uploadImage + analyzeImage 替代
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
  aiProvider = "glm",
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

// ========== AI客服API ==========

/**
 * 创建新会话
 */
export const createAISession = async () => {
  return apiClient.post("/ai-agent/sessions");
};

/**
 * 获取会话列表
 */
export const getAISessions = async () => {
  return apiClient.get("/ai-agent/sessions");
};

/**
 * 获取会话历史记录
 * @param {string} sessionId - 会话ID
 */
export const getAISessionHistory = async (sessionId) => {
  return apiClient.get(`/ai-agent/sessions/${sessionId}`);
};

/**
 * 获取热门问题列表
 */
export const getAIQuestions = async () => {
  return apiClient.get("/ai-agent/questions");
};

/**
 * 发送问题并获取回答
 * @param {string} sessionId - 会话ID
 * @param {string} question - 问题内容
 * @param {string} model - 模型类型 (deepseek/glm/qwen)
 * @param {boolean} deepThinking - 是否启用深度思考模式
 */
export const askAIQuestion = async (
  sessionId,
  question,
  model = "deepseek",
  deepThinking = false,
) => {
  return apiClient.post(
    "/ai-agent/ask",
    {
      session_id: sessionId,
      question: question,
      model: model,
      deep_thinking: deepThinking,
    },
    {
      timeout: 120000,
    },
  );
};

/**
 * 发送问题并获取回答（流式传输）
 * @param {string} sessionId - 会话ID
 * @param {string} question - 问题内容
 * @param {string} model - 模型类型 (deepseek/glm/qwen)
 * @param {boolean} deepThinking - 是否启用深度思考模式
 * @param {Function} onChunk - 接收数据块的回调函数
 * @param {Function} onComplete - 完成时的回调函数
 * @param {Function} onError - 错误时的回调函数
 */
export const askAIQuestionStream = async (
  sessionId,
  question,
  model = "deepseek",
  deepThinking = false,
  onChunk = null,
  onComplete = null,
  onError = null,
) => {
  const token = localStorage.getItem("token");
  const response = await fetch(`${API_BASE_URL}/ai-agent/ask-stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      session_id: sessionId,
      question: question,
      model: model,
      deep_thinking: deepThinking,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "请求失败");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      // 持续读取流式响应数据
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const dataStr = line.slice(6).trim();
          if (dataStr === "[DONE]") {
            if (onComplete) onComplete();
            return;
          }

          try {
            const data = JSON.parse(dataStr);
            if (onChunk) onChunk(data);
          } catch (e) {
            console.error("解析SSE数据失败:", e);
          }
        }
      }
    }
  } catch (error) {
    if (onError) onError(error);
    throw error;
  }
};

// ========== 认证API ==========

/**
 * 用户登录
 * @param {string} username - 用户名
 * @param {string} password - 密码
 */
export const login = async (username, password) => {
  const formData = new FormData();
  formData.append("username", username);
  formData.append("password", password);

  return apiClient.post("/auth/login", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

/**
 * 用户注册
 * @param {Object} userData - 用户数据
 * @param {string} userData.username - 用户名
 * @param {string} userData.email - 邮箱
 * @param {string} userData.phone - 手机号（可选）
 * @param {string} userData.password - 密码
 */
export const register = async (userData) => {
  return apiClient.post("/auth/register", userData);
};

/**
 * 获取当前用户信息
 */
export const getCurrentUser = async () => {
  return apiClient.get("/auth/me");
};

/**
 * 更新用户信息
 * @param {Object} userData - 用户数据
 * @param {string} userData.email - 邮箱
 * @param {string} userData.phone - 手机号
 */
export const updateUser = async (userData) => {
  return apiClient.put("/auth/me", userData);
};

/**
 * 上传用户头像
 * @param {File} file - 头像文件
 */
export const uploadAvatar = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  // 注意：上传文件时不要手动设置 Content-Type，让浏览器自动设置
  return apiClient.post("/auth/upload-avatar", formData);
};

// ========== 用户统计API ==========

/**
 * 获取用户统计概览
 */
export const getUserStats = async () => {
  return apiClient.get("/user-stats/overview");
};

/**
 * 记录查询历史
 * @param {string} typhoonId - 台风编号
 * @param {string} typhoonName - 台风名称
 */
export const addQueryHistory = async (typhoonId, typhoonName) => {
  return apiClient.post("/user-stats/query-history", {
    typhoon_id: typhoonId,
    typhoon_name: typhoonName,
  });
};

/**
 * 获取查询历史列表（按查询次数降序）
 * @param {number} limit - 返回记录数
 */
export const getQueryHistoryByCount = async (limit = 10) => {
  return apiClient.get("/user-stats/query-history/by-count", {
    params: { limit },
  });
};

/**
 * 获取收藏台风列表
 */
export const getCollectTyphoons = async () => {
  return apiClient.get("/user-stats/collect-typhoons");
};

/**
 * 收藏台风
 * @param {string} typhoonId - 台风编号
 * @param {string} typhoonName - 台风名称
 */
export const addCollectTyphoon = async (typhoonId, typhoonName) => {
  return apiClient.post("/user-stats/collect-typhoons", {
    typhoon_id: typhoonId,
    typhoon_name: typhoonName,
  });
};

/**
 * 取消收藏台风
 * @param {string} typhoonId - 台风编号
 */
export const removeCollectTyphoon = async (typhoonId) => {
  return apiClient.delete(`/user-stats/collect-typhoons/${typhoonId}`);
};

/**
 * 获取用户报告列表
 * @param {number} skip - 跳过记录数
 * @param {number} limit - 返回记录数
 */
export const getUserReports = async (skip = 0, limit = 50) => {
  return apiClient.get("/user-stats/reports", {
    params: { skip, limit },
  });
};

export default apiClient;
