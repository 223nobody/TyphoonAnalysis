/**
 * 统计分析面板组件
 */
import React, { useState } from "react";
import {
  getYearlyStatistics,
  getIntensityStatistics,
  compareTyphoons,
  exportTyphoon,
  exportBatchTyphoons,
} from "../services/api";

function StatisticsPanel() {
  const [statisticsType, setStatisticsType] = useState("yearly");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // 年度统计表单
  const [yearlyForm, setYearlyForm] = useState({
    startYear: 2020,
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
        yearlyForm.endYear
      );
      setResult({ type: "yearly", data });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 处理强度分布统计
  const handleIntensityStatistics = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getIntensityStatistics(
        intensityForm.year,
        intensityForm.typhoonId
      );
      setResult({ type: "intensity", data });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 处理台风对比
  const handleCompareTyphoons = async () => {
    if (!comparisonForm.typhoonIds) {
      alert("请输入台风ID列表");
      return;
    }

    const idArray = comparisonForm.typhoonIds
      .split(",")
      .map((id) => id.trim())
      .filter((id) => id);

    if (idArray.length === 0) {
      alert("请输入有效的台风ID");
      return;
    }

    if (idArray.length > 10) {
      alert("最多只能对比10个台风");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await compareTyphoons(idArray);
      setResult({ type: "comparison", data });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 处理单个导出
  const handleSingleExport = () => {
    if (!exportForm.typhoonId) {
      alert("请输入台风ID");
      return;
    }

    exportTyphoon(
      exportForm.typhoonId,
      exportForm.format,
      exportForm.includePath
    );
    alert(`正在导出台风 ${exportForm.typhoonId} 的数据，文件将自动下载...`);
  };

  // 处理批量导出
  const handleBatchExport = async () => {
    if (!exportForm.batchTyphoonIds) {
      alert("请输入台风ID列表");
      return;
    }

    const idArray = exportForm.batchTyphoonIds
      .split(",")
      .map((id) => id.trim())
      .filter((id) => id);

    if (idArray.length === 0) {
      alert("请输入有效的台风ID");
      return;
    }

    if (idArray.length > 50) {
      alert("最多只能批量导出50个台风");
      return;
    }

    try {
      setLoading(true);
      const result = await exportBatchTyphoons(
        idArray,
        exportForm.format,
        exportForm.includePath
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
        <label>台风ID列表（用逗号分隔）</label>
        <input
          type="text"
          placeholder="例如: 2501,2502,2503"
          value={comparisonForm.typhoonIds}
          onChange={(e) =>
            setComparisonForm({ ...comparisonForm, typhoonIds: e.target.value })
          }
        />
        <small>💡 最多可对比10个台风</small>
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
            <label>台风ID列表（用逗号分隔）</label>
            <input
              type="text"
              placeholder="例如: 2501,2502,2503"
              value={exportForm.batchTyphoonIds}
              onChange={(e) =>
                setExportForm({
                  ...exportForm,
                  batchTyphoonIds: e.target.value,
                })
              }
            />
            <small>💡 最多可批量导出50个台风</small>
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

  return (
    <div>
      <h2>📈 统计分析</h2>

      {/* 统计类型选择 */}
      <div className="form-group">
        <label>统计类型</label>
        <select
          value={statisticsType}
          onChange={(e) => setStatisticsType(e.target.value)}
        >
          <option value="yearly">年度统计</option>
          <option value="intensity">强度分布</option>
          <option value="comparison">台风对比</option>
          <option value="export">数据导出</option>
        </select>
      </div>

      {/* 根据类型渲染不同表单 */}
      {statisticsType === "yearly" && renderYearlyForm()}
      {statisticsType === "intensity" && renderIntensityForm()}
      {statisticsType === "comparison" && renderComparisonForm()}
      {statisticsType === "export" && renderExportForm()}

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

  // 渲染年度统计结果
  function renderYearlyResult(data) {
    return (
      <div>
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
        {data.intensity_distribution && (
          <div className="info-card">
            <h4>💨 强度分布</h4>
            {Object.entries(data.intensity_distribution).map(
              ([intensity, count]) => (
                <p key={intensity}>
                  <strong>{intensity}:</strong> {count}次
                </p>
              )
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
    );
  }
}

export default StatisticsPanel;
