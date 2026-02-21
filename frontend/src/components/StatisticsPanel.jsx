/**
 * 统计分析面板组件
 */
import { useState, useEffect, useRef } from "react";
import * as echarts from "echarts";
import {
  getYearlyStatistics,
  getIntensityStatistics,
  compareTyphoons,
  exportTyphoon,
  exportBatchTyphoons,
} from "../services/api";
import "../styles/StatisticsPanel.css";
import "../styles/common.css";

/**
 * 解析台风ID输入字符串，支持多种格式：
 * - 单个ID: "2501"
 * - 逗号分隔: "2501,2502,2503"
 * - 圆括号范围(开区间): "(2501,2510)" -> 2502-2509
 * - 方括号范围(闭区间): "[2501,2510]" -> 2501-2510
 * - 混合括号(半开半闭): "[2501,2510)" -> 2501-2509, "(2501,2510]" -> 2502-2510
 * - 混合格式: "2501,[2503,2505],(2507,2510)"
 *
 * @param {string} input - 用户输入的ID字符串
 * @returns {{ids: number[], error: string|null}} - 解析后的ID数组和错误信息
 */
function parseTyphoonIds(input) {
  if (!input || !input.trim()) {
    return { ids: [], error: "请输入台风ID" };
  }

  const trimmedInput = input.trim();
  const result = new Set();
  const errors = [];

  // 用于匹配范围的正则表达式
  // 支持 (start,end), [start,end], [start,end), (start,end]
  const rangePattern = /([\(\[])(\d+)\s*,\s*(\d+)([\)\]])/g;

  // 先提取所有范围表达式，避免与单个ID混淆
  const ranges = [];
  let match;
  let lastIndex = 0;

  while ((match = rangePattern.exec(trimmedInput)) !== null) {
    const [fullMatch, openBracket, startStr, endStr, closeBracket] = match;
    const start = parseInt(startStr, 10);
    const end = parseInt(endStr, 10);

    // 验证数字有效性
    if (isNaN(start) || isNaN(end)) {
      errors.push(`范围 "${fullMatch}" 包含无效的ID`);
      continue;
    }

    // 验证范围合理性
    if (start > end) {
      errors.push(`范围 "${fullMatch}" 起始值(${start})不能大于结束值(${end})`);
      continue;
    }

    // 确定包含边界
    const includeStart = openBracket === "[";
    const includeEnd = closeBracket === "]";

    // 计算实际范围
    const actualStart = includeStart ? start : start + 1;
    const actualEnd = includeEnd ? end : end - 1;

    // 验证范围有效性
    if (actualStart > actualEnd) {
      errors.push(
        `范围 "${fullMatch}" 无效：${includeStart ? "[" : "("}${start},${end}${includeEnd ? "]" : ")"} 不包含任何整数`,
      );
      continue;
    }

    // 限制范围大小（防止输入过大范围导致性能问题）
    const rangeSize = actualEnd - actualStart + 1;
    if (rangeSize > 100) {
      errors.push(
        `范围 "${fullMatch}" 包含${rangeSize}个ID，超过最大限制(100)`,
      );
      continue;
    }

    ranges.push({
      start: actualStart,
      end: actualEnd,
      fullMatch,
      index: match.index,
      length: fullMatch.length,
    });
  }

  // 构建排除范围后的字符串，用于提取单个ID
  let processedInput = trimmedInput;
  // 从后向前替换，避免索引变化
  for (let i = ranges.length - 1; i >= 0; i--) {
    const range = ranges[i];
    processedInput =
      processedInput.slice(0, range.index) +
      " " +
      processedInput.slice(range.index + range.length);
  }

  // 处理范围
  ranges.forEach((range) => {
    for (let id = range.start; id <= range.end; id++) {
      result.add(id);
    }
  });

  // 处理单个ID（逗号分隔）
  const singleIds = processedInput
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part.length > 0);

  singleIds.forEach((idStr) => {
    // 检查是否包含括号（未匹配到的无效括号）
    if (/[\(\[\]\)]/.test(idStr)) {
      errors.push(`"${idStr}" 格式错误：括号不匹配或位置不正确`);
      return;
    }

    const id = parseInt(idStr, 10);
    if (isNaN(id)) {
      errors.push(`"${idStr}" 不是有效的台风ID`);
      return;
    }
    result.add(id);
  });

  // 转换为数组并排序，然后转换为字符串（后端期望字符串数组）
  const idArray = Array.from(result)
    .sort((a, b) => a - b)
    .map((id) => String(id));

  // 验证总数限制
  if (idArray.length === 0) {
    return { ids: [], error: errors.join("; ") || "未找到有效的台风ID" };
  }

  return {
    ids: idArray,
    error: errors.length > 0 ? errors.join("; ") : null,
  };
}

function StatisticsPanel() {
  const [activeTab, setActiveTab] = useState("yearly");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // ECharts图表引用
  const yearlyChartRef = useRef(null);
  const intensityChartRef = useRef(null);
  const comparisonChartRef = useRef(null);

  // 年度统计表单
  const [yearlyForm, setYearlyForm] = useState({
    startYear: 2000,
    endYear: 2025,
  });

  // 强度分布表单
  const [intensityForm, setIntensityForm] = useState({
    year: "",
    typhoonId: "",
  });

  // 台风对比表单
  const [comparisonForm, setComparisonForm] = useState({
    typhoonIds: "",
  });

  // 数据导出表单
  const [exportForm, setExportForm] = useState({
    exportType: "single",
    typhoonId: "",
    format: "csv",
    includePath: true,
    batchTyphoonIds: "",
  });

  // 处理年度统计
  const handleYearlyStatistics = async () => {
    if (!yearlyForm.startYear || !yearlyForm.endYear) {
      alert("请输入起始年份和结束年份");
      return;
    }

    if (parseInt(yearlyForm.startYear) > parseInt(yearlyForm.endYear)) {
      alert("起始年份不能大于结束年份");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await getYearlyStatistics(
        yearlyForm.startYear,
        yearlyForm.endYear,
      );
      setResult({ type: "yearly", data });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 渲染年度统计ECharts图表
  useEffect(() => {
    if (
      result &&
      result.type === "yearly" &&
      result.data &&
      yearlyChartRef.current
    ) {
      const chartDom = yearlyChartRef.current;
      const myChart = echarts.init(chartDom);

      const yearlyData = result.data.yearly_data || [];
      const years = yearlyData.map((item) => item.year);
      const counts = yearlyData.map((item) => item.count);

      const option = {
        title: {
          text: "年度台风数量趋势",
          left: "center",
          textStyle: {
            color: "#333",
            fontSize: 16,
            fontWeight: "bold",
          },
        },
        tooltip: {
          trigger: "axis",
          axisPointer: {
            type: "shadow",
          },
          formatter: "{b}年: {c}个台风",
        },
        grid: {
          left: "10%",
          right: "10%",
          bottom: "15%",
          top: "15%",
          containLabel: true,
        },
        xAxis: {
          type: "category",
          data: years,
          axisLabel: {
            rotate: 45,
            fontSize: 12,
          },
          name: "年份",
          nameTextStyle: {
            fontSize: 14,
            fontWeight: "bold",
          },
        },
        yAxis: {
          type: "value",
          name: "台风数量",
          nameTextStyle: {
            fontSize: 14,
            fontWeight: "bold",
          },
          axisLabel: {
            formatter: "{value}个",
          },
        },
        series: [
          {
            name: "台风数量",
            type: "line",
            data: counts,
            smooth: true,
            lineStyle: {
              width: 3,
              color: "#667eea",
            },
            itemStyle: {
              color: "#667eea",
              borderWidth: 2,
              borderColor: "#fff",
            },
            areaStyle: {
              color: {
                type: "linear",
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: "rgba(102, 126, 234, 0.3)" },
                  { offset: 1, color: "rgba(102, 126, 234, 0.05)" },
                ],
              },
            },
            emphasis: {
              focus: "series",
              itemStyle: {
                color: "#764ba2",
                borderWidth: 3,
              },
            },
          },
        ],
      };

      myChart.setOption(option);

      // 响应式调整
      const resizeHandler = () => myChart.resize();
      window.addEventListener("resize", resizeHandler);

      return () => {
        window.removeEventListener("resize", resizeHandler);
        myChart.dispose();
      };
    }
  }, [result]);

  // 处理强度分布统计
  const handleIntensityStatistics = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getIntensityStatistics(
        intensityForm.year,
        intensityForm.typhoonId,
      );
      setResult({ type: "intensity", data });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 渲染强度分布ECharts图表
  useEffect(() => {
    if (
      result &&
      result.type === "intensity" &&
      result.data &&
      intensityChartRef.current
    ) {
      const chartDom = intensityChartRef.current;
      const myChart = echarts.init(chartDom);

      const intensityData = result.data.intensity_distribution || {};
      const data = Object.entries(intensityData).map(([name, value]) => ({
        name,
        value,
      }));

      // 强度等级颜色映射
      const colorMap = {
        热带低压: "#3498db",
        热带风暴: "#2ecc71",
        强热带风暴: "#f1c40f",
        台风: "#e67e22",
        强台风: "#e74c3c",
        超强台风: "#c0392b",
      };

      const option = {
        title: {
          text: "台风强度分布",
          left: "center",
          textStyle: {
            color: "#333",
            fontSize: 16,
            fontWeight: "bold",
          },
        },
        tooltip: {
          trigger: "item",
          formatter: "{b}: {c}个 ({d}%)",
        },
        legend: {
          orient: "vertical",
          left: "left",
          top: "middle",
          textStyle: {
            fontSize: 12,
          },
        },
        series: [
          {
            name: "强度分布",
            type: "pie",
            radius: ["40%", "70%"],
            center: ["60%", "50%"],
            avoidLabelOverlap: true,
            itemStyle: {
              borderRadius: 10,
              borderColor: "#fff",
              borderWidth: 2,
            },
            label: {
              show: true,
              formatter: "{b}\n{c}个 ({d}%)",
              fontSize: 12,
            },
            emphasis: {
              label: {
                show: true,
                fontSize: 14,
                fontWeight: "bold",
              },
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: "rgba(0, 0, 0, 0.5)",
              },
            },
            data: data.map((item) => ({
              ...item,
              itemStyle: {
                color: colorMap[item.name] || "#95a5a6",
              },
            })),
          },
        ],
      };

      myChart.setOption(option);

      // 响应式调整
      const resizeHandler = () => myChart.resize();
      window.addEventListener("resize", resizeHandler);

      return () => {
        window.removeEventListener("resize", resizeHandler);
        myChart.dispose();
      };
    }
  }, [result]);

  // 处理台风对比
  const handleCompareTyphoons = async () => {
    if (!comparisonForm.typhoonIds) {
      alert("请输入台风ID列表");
      return;
    }

    const { ids, error: parseError } = parseTyphoonIds(
      comparisonForm.typhoonIds,
    );

    if (parseError && ids.length === 0) {
      alert(`输入格式错误: ${parseError}`);
      return;
    }

    if (ids.length === 0) {
      alert("请输入有效的台风ID");
      return;
    }

    if (ids.length > 10) {
      alert(`最多只能对比10个台风，当前选择了${ids.length}个`);
      return;
    }

    // 如果有警告但不影响主要功能，显示警告但继续执行
    if (parseError) {
      console.warn("ID解析警告:", parseError);
    }

    try {
      setLoading(true);
      setError(null);
      const data = await compareTyphoons(ids);
      setResult({ type: "comparison", data });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 渲染台风对比ECharts图表
  useEffect(() => {
    if (
      result &&
      result.type === "comparison" &&
      result.data &&
      result.data.typhoons &&
      comparisonChartRef.current
    ) {
      const chartDom = comparisonChartRef.current;
      const myChart = echarts.init(chartDom);

      const typhoons = result.data.typhoons || [];
      const typhoonNames = typhoons.map(
        (t) => t.typhoon_name_cn || t.typhoon_name || t.typhoon_id,
      );
      const maxWindSpeeds = typhoons.map((t) => t.max_wind_speed || 0);
      const minPressures = typhoons.map((t) => t.min_pressure || 0);

      const option = {
        title: {
          text: "台风对比分析",
          left: "center",
          textStyle: {
            color: "#333",
            fontSize: 16,
            fontWeight: "bold",
          },
        },
        tooltip: {
          trigger: "axis",
          axisPointer: {
            type: "shadow",
          },
        },
        legend: {
          data: ["最大风速 (m/s)", "最低气压 (hPa)"],
          top: "10%",
        },
        grid: {
          left: "10%",
          right: "10%",
          bottom: "15%",
          top: "20%",
          containLabel: true,
        },
        xAxis: {
          type: "category",
          data: typhoonNames,
          axisLabel: {
            rotate: 30,
            fontSize: 11,
            interval: 0,
          },
        },
        yAxis: [
          {
            type: "value",
            name: "风速 (m/s)",
            position: "left",
            axisLabel: {
              formatter: "{value}",
            },
          },
          {
            type: "value",
            name: "气压 (hPa)",
            position: "right",
            axisLabel: {
              formatter: "{value}",
            },
          },
        ],
        series: [
          {
            name: "最大风速 (m/s)",
            type: "bar",
            data: maxWindSpeeds,
            itemStyle: {
              color: "#667eea",
            },
            emphasis: {
              itemStyle: {
                color: "#764ba2",
              },
            },
            label: {
              show: true,
              position: "top",
              formatter: "{c}",
              fontSize: 10,
            },
          },
          {
            name: "最低气压 (hPa)",
            type: "line",
            yAxisIndex: 1,
            data: minPressures,
            lineStyle: {
              width: 3,
              color: "#e74c3c",
            },
            itemStyle: {
              color: "#e74c3c",
              borderWidth: 2,
              borderColor: "#fff",
            },
            label: {
              show: true,
              position: "bottom",
              formatter: "{c}",
              fontSize: 10,
              color: "#e74c3c",
            },
          },
        ],
      };

      myChart.setOption(option);

      // 响应式调整
      const resizeHandler = () => myChart.resize();
      window.addEventListener("resize", resizeHandler);

      return () => {
        window.removeEventListener("resize", resizeHandler);
        myChart.dispose();
      };
    }
  }, [result]);

  // 处理单个导出
  const handleSingleExport = () => {
    if (!exportForm.typhoonId) {
      alert("请输入台风ID");
      return;
    }

    exportTyphoon(
      exportForm.typhoonId,
      exportForm.format,
      exportForm.includePath,
    );
    alert(`正在导出台风 ${exportForm.typhoonId} 的数据，文件将自动下载...`);
  };

  // 处理批量导出
  const handleBatchExport = async () => {
    if (!exportForm.batchTyphoonIds) {
      alert("请输入台风ID列表");
      return;
    }

    const { ids, error: parseError } = parseTyphoonIds(
      exportForm.batchTyphoonIds,
    );

    if (parseError && ids.length === 0) {
      alert(`输入格式错误: ${parseError}`);
      return;
    }

    if (ids.length === 0) {
      alert("请输入有效的台风ID");
      return;
    }

    if (ids.length > 50) {
      alert(`最多只能批量导出50个台风，当前选择了${ids.length}个`);
      return;
    }

    // 如果有警告但不影响主要功能，显示警告但继续执行
    if (parseError) {
      console.warn("ID解析警告:", parseError);
    }

    try {
      setLoading(true);
      const result = await exportBatchTyphoons(
        ids,
        exportForm.format,
        exportForm.includePath,
      );
      alert(`成功导出 ${result.count} 个台风的数据！`);
    } catch (err) {
      alert(`批量导出失败: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 渲染年度统计表单
  const renderYearlyForm = () => (
    <div>
      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px" }}
      >
        <div className="form-group">
          <label>起始年份</label>
          <input
            type="number"
            placeholder="例如: 2020"
            min="2000"
            max="2030"
            value={yearlyForm.startYear}
            onChange={(e) =>
              setYearlyForm({ ...yearlyForm, startYear: e.target.value })
            }
          />
        </div>
        <div className="form-group">
          <label>结束年份</label>
          <input
            type="number"
            placeholder="例如: 2025"
            min="2000"
            max="2030"
            value={yearlyForm.endYear}
            onChange={(e) =>
              setYearlyForm({ ...yearlyForm, endYear: e.target.value })
            }
          />
        </div>
      </div>
      <button
        className="btn"
        onClick={handleYearlyStatistics}
        disabled={loading}
      >
        📊 查询年度统计
      </button>
    </div>
  );

  // 渲染强度分布表单
  const renderIntensityForm = () => (
    <div>
      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px" }}
      >
        <div className="form-group">
          <label>年份（可选）</label>
          <input
            type="number"
            placeholder="留空则统计所有年份"
            min="2000"
            max="2030"
            value={intensityForm.year}
            onChange={(e) =>
              setIntensityForm({ ...intensityForm, year: e.target.value })
            }
          />
        </div>
        <div className="form-group">
          <label>台风ID（可选）</label>
          <input
            type="text"
            placeholder="留空则统计所有台风"
            value={intensityForm.typhoonId}
            onChange={(e) =>
              setIntensityForm({ ...intensityForm, typhoonId: e.target.value })
            }
          />
        </div>
      </div>
      <button
        className="btn"
        onClick={handleIntensityStatistics}
        disabled={loading}
      >
        📊 查询强度分布
      </button>
    </div>
  );

  // 渲染台风对比表单
  const renderComparisonForm = () => (
    <div>
      <div className="form-group">
        <label>台风ID列表</label>
        <input
          type="text"
          placeholder="例如: 2501,2502,2503 或 [2501,2505],(2510,2515)"
          value={comparisonForm.typhoonIds}
          onChange={(e) =>
            setComparisonForm({ ...comparisonForm, typhoonIds: e.target.value })
          }
        />
        <div
          className="input-help"
          style={{ marginTop: "8px", fontSize: "12px", color: "#6b7280" }}
        >
          <p style={{ margin: "0 0 4px 0" }}>💡 支持以下格式（可混合使用）:</p>
          <ul style={{ margin: "0", paddingLeft: "16px" }}>
            <li>
              逗号分隔: <code>2501,2502,2503</code>
            </li>
            <li>
              混合括号: <code>[2501,2505)</code> = 2501,2502,2503,2504
            </li>
            <li>
              混合格式: <code>2501,[2503,2505],(2507,2510)</code>
            </li>
          </ul>
          <p style={{ margin: "4px 0 0 0", color: "#ef4444" }}>
            ⚠️ 最多可对比10个台风
          </p>
        </div>
      </div>
      <button
        className="btn"
        onClick={handleCompareTyphoons}
        disabled={loading}
      >
        📊 开始对比
      </button>
    </div>
  );

  // 渲染数据导出表单
  const renderExportForm = () => (
    <div>
      <div className="form-group">
        <label>导出类型</label>
        <select
          value={exportForm.exportType}
          onChange={(e) =>
            setExportForm({ ...exportForm, exportType: e.target.value })
          }
        >
          <option value="single">单个台风导出</option>
          <option value="batch">批量台风导出</option>
        </select>
      </div>

      {exportForm.exportType === "single" ? (
        <div>
          <div className="form-group">
            <label>台风ID</label>
            <input
              type="text"
              placeholder="例如: 2501"
              value={exportForm.typhoonId}
              onChange={(e) =>
                setExportForm({ ...exportForm, typhoonId: e.target.value })
              }
            />
          </div>
          <div className="form-group">
            <label>导出格式</label>
            <select
              value={exportForm.format}
              onChange={(e) =>
                setExportForm({ ...exportForm, format: e.target.value })
              }
            >
              <option value="csv">CSV格式（Excel友好）</option>
              <option value="json">JSON格式（程序处理）</option>
            </select>
          </div>
          <div className="form-group">
            <label
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "flex-start",
                cursor: "pointer",
                width: "auto",
              }}
            >
              <input
                type="checkbox"
                checked={exportForm.includePath}
                onChange={(e) =>
                  setExportForm({
                    ...exportForm,
                    includePath: e.target.checked,
                  })
                }
                style={{ width: "auto", margin: 0 }}
              />
              <span style={{ marginLeft: "8px", fontSize: 17 }}>
                包含路径数据
              </span>
            </label>
          </div>
          <button
            className="btn"
            onClick={handleSingleExport}
            disabled={loading}
          >
            📥 导出数据
          </button>
        </div>
      ) : (
        <div>
          <div className="form-group">
            <label>台风ID列表</label>
            <input
              type="text"
              placeholder="例如: 2501,2502,2503 或 [2501,2510],(2520,2530)"
              value={exportForm.batchTyphoonIds}
              onChange={(e) =>
                setExportForm({
                  ...exportForm,
                  batchTyphoonIds: e.target.value,
                })
              }
            />
            <div
              className="input-help"
              style={{ marginTop: "8px", fontSize: "12px", color: "#6b7280" }}
            >
              <p style={{ margin: "0 0 4px 0" }}>
                💡 支持以下格式（可混合使用）:
              </p>
              <ul style={{ margin: "0", paddingLeft: "16px" }}>
                <li>
                  逗号分隔: <code>2501,2502,2503</code>
                </li>
                <li>
                  混合括号: <code>[2501,2505)</code> = 2501-2504（包含起始）
                </li>
                <li>
                  混合格式: <code>2501,[2503,2505],(2507,2510)</code>
                </li>
              </ul>
              <p style={{ margin: "4px 0 0 0", color: "#ef4444" }}>
                ⚠️ 最多可批量导出50个台风
              </p>
            </div>
          </div>
          <div className="form-group">
            <label>导出格式</label>
            <select
              value={exportForm.format}
              onChange={(e) =>
                setExportForm({ ...exportForm, format: e.target.value })
              }
            >
              <option value="csv">CSV格式（Excel友好）</option>
              <option value="json">JSON格式（程序处理）</option>
            </select>
          </div>
          <div className="form-group">
            <label
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "flex-start",
                cursor: "pointer",
                width: "auto",
              }}
            >
              <input
                type="checkbox"
                checked={exportForm.includePath}
                onChange={(e) =>
                  setExportForm({
                    ...exportForm,
                    includePath: e.target.checked,
                  })
                }
                style={{ width: "auto", margin: 0 }}
              />
              <span style={{ marginLeft: "8px" }}>包含路径数据</span>
            </label>
          </div>
          <button
            className="btn"
            onClick={handleBatchExport}
            disabled={loading}
          >
            📥 批量导出
          </button>
        </div>
      )}

      <div className="info-card" style={{ marginTop: "15px" }}>
        <p style={{ margin: 0, fontSize: "13px", color: "#1e40af" }}>
          💡 <strong>导出说明：</strong>
        </p>
        <ul
          style={{ margin: "8px 0 0 20px", fontSize: "12px", color: "#1e40af" }}
        >
          <li>CSV格式：适合在Excel中打开和分析</li>
          <li>JSON格式：适合程序处理和数据交换</li>
          <li>包含路径数据：导出完整的台风路径点信息</li>
          <li>文件将自动下载到浏览器默认下载目录</li>
        </ul>
      </div>
    </div>
  );

  // 渲染年度统计结果
  function renderYearlyResult(data) {
    return (
      <div>
        <div
          ref={yearlyChartRef}
          style={{
            width: "100%",
            height: "400px",
            marginBottom: "20px",
            border: "1px solid #e5e7eb",
            borderRadius: "8px",
            padding: "10px",
            backgroundColor: "#fff",
          }}
        ></div>

        <div className="info-card">
          <h4>📊 年度统计汇总</h4>
          {data.summary && (
            <>
              <p>
                <strong>总台风数:</strong> {data.summary.total_typhoons || 0}
              </p>
              <p>
                <strong>平均每年:</strong> {data.summary.avg_per_year || 0}
              </p>
              <p>
                <strong>最多年份:</strong> {data.summary.max_year || "N/A"} (
                {data.summary.max_count || 0}个)
              </p>
              <p>
                <strong>最少年份:</strong> {data.summary.min_year || "N/A"} (
                {data.summary.min_count || 0}个)
              </p>
            </>
          )}
        </div>

        {data.yearly_data && data.yearly_data.length > 0 && (
          <div className="info-card">
            <h4>📈 各年度详情</h4>
            <table>
              <thead>
                <tr>
                  <th>年份</th>
                  <th>台风数量</th>
                </tr>
              </thead>
              <tbody>
                {data.yearly_data.map((item) => (
                  <tr key={item.year}>
                    <td style={{ textAlign: "center" }}>{item.year}</td>
                    <td style={{ textAlign: "center" }}>{item.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  // 渲染强度分布结果
  function renderIntensityResult(data) {
    return (
      <div>
        {/* ECharts图表容器 */}
        <div
          ref={intensityChartRef}
          style={{
            width: "100%",
            height: "450px",
            marginBottom: "20px",
            border: "1px solid #e5e7eb",
            borderRadius: "8px",
            padding: "10px",
            backgroundColor: "#fff",
          }}
        ></div>

        {data.intensity_distribution && (
          <div className="info-card">
            <h4>💨 强度分布</h4>
            {Object.entries(data.intensity_distribution).map(
              ([intensity, count]) => (
                <p key={intensity}>
                  <strong>{intensity}:</strong> {count}次
                </p>
              ),
            )}
          </div>
        )}

        {data.wind_speed_ranges && (
          <div className="info-card">
            <h4>🌪️ 风速范围分布</h4>
            {Object.entries(data.wind_speed_ranges).map(([range, count]) => (
              <p key={range}>
                <strong>{range}:</strong> {count}次
              </p>
            ))}
          </div>
        )}

        {data.pressure_ranges && (
          <div className="info-card">
            <h4>🌡️ 气压范围分布</h4>
            {Object.entries(data.pressure_ranges).map(([range, count]) => (
              <p key={range}>
                <strong>{range}:</strong> {count}次
              </p>
            ))}
          </div>
        )}
      </div>
    );
  }

  // 渲染台风对比结果
  function renderComparisonResult(data) {
    if (!data.typhoons || data.typhoons.length === 0) {
      return <p>暂无对比数据</p>;
    }

    return (
      <div>
        {/* ECharts图表容器 */}
        <div
          ref={comparisonChartRef}
          style={{
            width: "100%",
            height: "400px",
            marginBottom: "20px",
            border: "1px solid #e5e7eb",
            borderRadius: "8px",
            padding: "10px",
            backgroundColor: "#fff",
          }}
        ></div>

        <div className="info-card">
          <h4>🔍 台风对比结果</h4>
          <table style={{ fontSize: "12px" }}>
            <thead>
              <tr>
                <th>台风ID</th>
                <th>名称</th>
                <th>年份</th>
                <th>最大强度</th>
                <th>最大风速</th>
                <th>最低气压</th>
              </tr>
            </thead>
            <tbody>
              {data.typhoons.map((t) => (
                <tr key={t.typhoon_id}>
                  <td style={{ textAlign: "center" }}>{t.typhoon_id}</td>
                  <td>{t.typhoon_name_cn || t.typhoon_name}</td>
                  <td style={{ textAlign: "center" }}>{t.year}</td>
                  <td style={{ textAlign: "center" }}>
                    {t.max_intensity || "N/A"}
                  </td>
                  <td style={{ textAlign: "center" }}>
                    {t.max_wind_speed ? `${t.max_wind_speed}m/s` : "N/A"}
                  </td>
                  <td style={{ textAlign: "center" }}>
                    {t.min_pressure ? `${t.min_pressure}hPa` : "N/A"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // 渲染结果
  function renderResult() {
    if (!result || !result.data) return null;

    return (
      <div className="result-box" style={{ marginTop: "20px" }}>
        <h3>统计结果</h3>
        {result.type === "yearly" && renderYearlyResult(result.data)}
        {result.type === "intensity" && renderIntensityResult(result.data)}
        {result.type === "comparison" && renderComparisonResult(result.data)}
      </div>
    );
  }

  return (
    <div>
      <h2>📈 统计分析</h2>

      {/* 统计类型标签页 */}
      <div style={{ marginBottom: "20px", borderBottom: "2px solid #e5e7eb" }}>
        <button
          onClick={() => {
            setActiveTab("yearly");
            setResult(null);
            setError(null);
          }}
          style={{
            padding: "12px 24px",
            fontSize: "16px",
            fontWeight: "bold",
            border: "none",
            background: "transparent",
            borderBottom: activeTab === "yearly" ? "3px solid #3b82f6" : "none",
            color: activeTab === "yearly" ? "#3b82f6" : "#6b7280",
            cursor: "pointer",
            marginRight: "10px",
          }}
        >
          年度统计
        </button>
        <button
          onClick={() => {
            setActiveTab("intensity");
            setResult(null);
            setError(null);
          }}
          style={{
            padding: "12px 24px",
            fontSize: "16px",
            fontWeight: "bold",
            border: "none",
            background: "transparent",
            borderBottom:
              activeTab === "intensity" ? "3px solid #3b82f6" : "none",
            color: activeTab === "intensity" ? "#3b82f6" : "#6b7280",
            cursor: "pointer",
            marginRight: "10px",
          }}
        >
          强度分布
        </button>
        <button
          onClick={() => {
            setActiveTab("comparison");
            setResult(null);
            setError(null);
          }}
          style={{
            padding: "12px 24px",
            fontSize: "16px",
            fontWeight: "bold",
            border: "none",
            background: "transparent",
            borderBottom:
              activeTab === "comparison" ? "3px solid #3b82f6" : "none",
            color: activeTab === "comparison" ? "#3b82f6" : "#6b7280",
            cursor: "pointer",
            marginRight: "10px",
          }}
        >
          台风对比
        </button>
        <button
          onClick={() => {
            setActiveTab("export");
            setResult(null);
            setError(null);
          }}
          style={{
            padding: "12px 24px",
            fontSize: "16px",
            fontWeight: "bold",
            border: "none",
            background: "transparent",
            borderBottom: activeTab === "export" ? "3px solid #3b82f6" : "none",
            color: activeTab === "export" ? "#3b82f6" : "#6b7280",
            cursor: "pointer",
          }}
        >
          数据导出
        </button>
      </div>

      {/* 根据类型渲染不同表单 */}
      {activeTab === "yearly" && renderYearlyForm()}
      {activeTab === "intensity" && renderIntensityForm()}
      {activeTab === "comparison" && renderComparisonForm()}
      {activeTab === "export" && renderExportForm()}

      {/* 错误提示 */}
      {error && (
        <div className="error-message" style={{ marginTop: "20px" }}>
          ❌ {error}
        </div>
      )}

      {/* 加载状态 */}
      {loading && <div className="loading">处理中</div>}

      {/* 结果显示 */}
      {result && renderResult()}
    </div>
  );
}

export default StatisticsPanel;
