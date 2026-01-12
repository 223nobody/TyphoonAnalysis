/**
 * 地图可视化组件 - 包含左侧台风列表和右侧地图
 * 参考原HTML版本的实现逻辑
 */
import React, { useState, useEffect, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Tooltip,
} from "react-leaflet";
import { getTyphoonList, getTyphoonPath } from "../services/api";
import "leaflet/dist/leaflet.css";

function MapVisualization({ selectedTyphoons, onTyphoonSelect }) {
  // 台风列表相关状态
  const [typhoons, setTyphoons] = useState([]);
  const [filteredTyphoons, setFilteredTyphoons] = useState([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState(null);

  // 筛选条件
  const [filters, setFilters] = useState({
    year: "2025", // 默认2025年
    status: "",
    search: "",
  });

  // 地图路径相关状态
  const [pathsData, setPathsData] = useState(new Map());
  const [pathLoading, setPathLoading] = useState(false);
  const [pathError, setPathError] = useState(null);
  const mapRef = useRef(null);

  // 多台风叠加显示选项（默认为true）
  const [allowMultipleTyphoons, setAllowMultipleTyphoons] = useState(true);

  // 加载台风列表
  useEffect(() => {
    loadTyphoons();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.year, filters.status]); // 当年份或状态筛选条件变化时重新加载

  // 应用前端搜索筛选（仅用于名称搜索）
  useEffect(() => {
    applyFilters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typhoons, filters.search]); // 当台风数据或搜索关键词变化时重新筛选

  // 当选中的台风变化时，加载路径数据
  useEffect(() => {
    if (selectedTyphoons && selectedTyphoons.size > 0) {
      loadTyphoonPaths();
    } else {
      setPathsData(new Map());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTyphoons]);

  // 加载台风列表 - 修复：传递年份参数到后端API
  const loadTyphoons = async () => {
    try {
      setListLoading(true);
      setListError(null);

      // 构建查询参数
      const params = {
        limit: 100, // 修复：后端限制最大值为100
      };

      // 如果选择了年份，传递给后端
      if (filters.year) {
        params.year = parseInt(filters.year);
      }

      // 如果选择了状态，传递给后端
      if (filters.status !== "") {
        params.status = parseInt(filters.status);
      }

      const data = await getTyphoonList(params);

      if (data && data.items && Array.isArray(data.items)) {
        setTyphoons(data.items);
      } else if (data && Array.isArray(data)) {
        setTyphoons(data);
      } else {
        console.error("API返回数据格式错误:", data);
        setListError("加载台风列表失败：数据格式错误");
      }
    } catch (err) {
      console.error("加载台风列表失败:", err);
      setListError(err.message || "加载失败，请检查后端服务是否正常运行");
    } finally {
      setListLoading(false);
    }
  };

  // 应用前端筛选（仅处理搜索关键词，年份和状态已在后端筛选）
  const applyFilters = () => {
    let filtered = [...typhoons];

    // 搜索筛选（在前端处理，因为需要模糊匹配）
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(
        (t) =>
          t.typhoon_id.toLowerCase().includes(searchLower) ||
          t.typhoon_name.toLowerCase().includes(searchLower) ||
          (t.typhoon_name_cn && t.typhoon_name_cn.includes(filters.search))
      );
    }

    setFilteredTyphoons(filtered);
  };

  // 加载台风路径
  const loadTyphoonPaths = async () => {
    try {
      setPathLoading(true);
      setPathError(null);
      const newPathsData = new Map();

      for (const typhoonId of selectedTyphoons) {
        try {
          const data = await getTyphoonPath(typhoonId);
          if (data && data.items && Array.isArray(data.items)) {
            newPathsData.set(typhoonId, data.items);
          } else if (data && Array.isArray(data)) {
            newPathsData.set(typhoonId, data);
          } else {
            console.warn(`台风 ${typhoonId} 路径数据格式错误:`, data);
          }
        } catch (err) {
          console.error(`加载台风 ${typhoonId} 路径失败:`, err);
        }
      }

      setPathsData(newPathsData);
    } catch (err) {
      console.error("加载台风路径失败:", err);
      setPathError(err.message || "加载失败，请稍后重试");
    } finally {
      setPathLoading(false);
    }
  };

  // 处理台风选择
  const handleTyphoonClick = (typhoonId) => {
    if (onTyphoonSelect) {
      onTyphoonSelect(typhoonId);
    }
  };

  // 获取年份列表（从当前年份到2000年）- 修复年份范围
  const getYears = () => {
    const currentYear = new Date().getFullYear();
    const years = [];
    for (let year = currentYear; year >= 2000; year--) {
      years.push(year);
    }
    return years;
  };

  // 根据强度获取颜色
  const getColorByIntensity = (intensity) => {
    const colorMap = {
      热带低压: "#3498db",
      热带风暴: "#2ecc71",
      强热带风暴: "#f1c40f",
      台风: "#e67e22",
      强台风: "#e74c3c",
      超强台风: "#c0392b",
    };
    return colorMap[intensity] || "#667eea";
  };

  // 根据风速获取半径 - 严格按照需求规范
  const getRadiusByWindSpeed = (windSpeed) => {
    if (!windSpeed) return 4; // 默认最小
    if (windSpeed < 20) return 4; // 风速 < 20 m/s：小圆点（半径4px）
    if (windSpeed < 30) return 6; // 风速 20-30 m/s：中等圆点（半径6px）
    if (windSpeed < 40) return 8; // 风速 30-40 m/s：较大圆点（半径8px）
    if (windSpeed < 50) return 10; // 风速 40-50 m/s：大圆点（半径10px）
    return 12; // 风速 > 50 m/s：最大圆点（半径12px）
  };

  // 创建弹窗内容
  const createPopupContent = (point) => {
    // 修复字段名映射
    const timestamp = point.timestamp || point.record_time || point.time;
    const windSpeed = point.max_wind_speed || point.wind_speed;
    const pressure = point.center_pressure || point.pressure;
    const movingSpeed = point.moving_speed;
    const movingDirection = point.moving_direction;

    return (
      <div style={{ minWidth: "220px", fontSize: "13px", lineHeight: "1.6" }}>
        <h4
          style={{
            margin: "0 0 10px 0",
            fontSize: "14px",
            color: "#667eea",
            fontWeight: "bold",
          }}
        >
          台风路径点信息
        </h4>
        <p style={{ margin: "5px 0" }}>
          <strong>时间：</strong>
          {timestamp ? new Date(timestamp).toLocaleString("zh-CN") : "暂无数据"}
        </p>
        <p style={{ margin: "5px 0" }}>
          <strong>位置：</strong>北纬 {point.latitude?.toFixed(2)}°，东经{" "}
          {point.longitude?.toFixed(2)}°
        </p>
        <p style={{ margin: "5px 0" }}>
          <strong>中心气压：</strong>
          {pressure ? `${pressure} hPa` : "暂无数据"}
        </p>
        <p style={{ margin: "5px 0" }}>
          <strong>最大风速：</strong>
          {windSpeed ? `${windSpeed} m/s` : "暂无数据"}
        </p>
        <p style={{ margin: "5px 0" }}>
          <strong>移动速度：</strong>
          {movingSpeed ? `${movingSpeed} km/h` : "暂无数据"}
        </p>
        <p style={{ margin: "5px 0" }}>
          <strong>移动方向：</strong>
          {movingDirection || "暂无数据"}
        </p>
        <p style={{ margin: "5px 0" }}>
          <strong>强度等级：</strong>
          {point.intensity || "暂无数据"}
        </p>
      </div>
    );
  };

  return (
    <div
      style={{
        display: "flex",
        gap: "20px",
        height: "calc(100vh - 180px)",
        minHeight: "800px",
      }}
    >
      {/* 左侧台风列表面板 */}
      <div
        style={{
          width: "300px",
          background: "#f9fafb",
          borderRadius: "10px",
          padding: "20px",
          overflowY: "auto",
        }}
      >
        <h3 style={{ marginTop: 0, marginBottom: "15px" }}>台风列表</h3>

        {/* 筛选器 */}
        <div style={{ marginBottom: "15px" }}>
          <div className="form-group" style={{ marginBottom: "10px" }}>
            <label>年份</label>
            <select
              value={filters.year}
              onChange={(e) => setFilters({ ...filters, year: e.target.value })}
            >
              <option value="">全部年份</option>
              {getYears().map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group" style={{ marginBottom: "10px" }}>
            <label>状态</label>
            <select
              value={filters.status}
              onChange={(e) =>
                setFilters({ ...filters, status: e.target.value })
              }
            >
              <option value="">全部状态</option>
              <option value="1">活跃中</option>
              <option value="0">已停止</option>
            </select>
          </div>

          <div className="form-group" style={{ marginBottom: "10px" }}>
            <label>搜索</label>
            <input
              type="text"
              placeholder="搜索台风名称或ID"
              value={filters.search}
              onChange={(e) =>
                setFilters({ ...filters, search: e.target.value })
              }
            />
          </div>

          {/* 多台风叠加显示选项 */}
          <div
            style={{
              marginTop: "15px",
              padding: "12px",
              background: "#f0f9ff",
              borderRadius: "8px",
              border: "1px solid #bfdbfe",
            }}
          >
            <label
              style={{
                display: "flex",
                alignItems: "center",
                cursor: "pointer",
                fontSize: "14px",
                color: "#1e40af",
              }}
            >
              <input
                type="checkbox"
                checked={allowMultipleTyphoons}
                onChange={(e) => setAllowMultipleTyphoons(e.target.checked)}
                style={{
                  marginRight: "8px",
                  width: "16px",
                  height: "16px",
                  cursor: "pointer",
                }}
              />
              <span style={{ fontWeight: "500" }}>多台风叠加显示</span>
            </label>
            <p
              style={{
                margin: "5px 0 0 24px",
                fontSize: "12px",
                color: "#6b7280",
              }}
            >
              {allowMultipleTyphoons
                ? "✓ 可同时显示多个台风路径"
                : "✗ 选择新台风时清除之前的路径"}
            </p>
          </div>
        </div>

        {/* 加载状态 */}
        {listLoading && (
          <div
            style={{ textAlign: "center", padding: "20px", color: "#6b7280" }}
          >
            正在加载台风数据...
          </div>
        )}

        {/* 错误提示 */}
        {listError && (
          <div className="error-message" style={{ marginBottom: "15px" }}>
            ❌ {listError}
          </div>
        )}

        {/* 台风列表 */}
        {!listLoading && !listError && (
          <div>
            <p
              style={{
                fontSize: "13px",
                color: "#6b7280",
                marginBottom: "10px",
              }}
            >
              共 {filteredTyphoons.length} 个台风
            </p>
            <div
              style={{ display: "flex", flexDirection: "column", gap: "8px" }}
            >
              {filteredTyphoons.map((typhoon) => (
                <div
                  key={typhoon.typhoon_id}
                  onClick={() => handleTyphoonClick(typhoon.typhoon_id)}
                  style={{
                    padding: "12px",
                    background:
                      selectedTyphoons &&
                      selectedTyphoons.has(typhoon.typhoon_id)
                        ? "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
                        : "white",
                    color:
                      selectedTyphoons &&
                      selectedTyphoons.has(typhoon.typhoon_id)
                        ? "white"
                        : "#1f2937",
                    borderRadius: "8px",
                    cursor: "pointer",
                    transition: "all 0.3s ease",
                    border: "1px solid #e5e7eb",
                  }}
                  onMouseEnter={(e) => {
                    if (
                      !selectedTyphoons ||
                      !selectedTyphoons.has(typhoon.typhoon_id)
                    ) {
                      e.currentTarget.style.background = "#f3f4f6";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (
                      !selectedTyphoons ||
                      !selectedTyphoons.has(typhoon.typhoon_id)
                    ) {
                      e.currentTarget.style.background = "white";
                    }
                  }}
                >
                  <div style={{ fontWeight: "bold", marginBottom: "5px" }}>
                    {typhoon.typhoon_name_cn ||
                      typhoon.typhoon_name ||
                      typhoon.typhoon_id}
                  </div>
                  <div style={{ fontSize: "12px", opacity: 0.9 }}>
                    ID: {typhoon.typhoon_id} | {typhoon.year}年 |{" "}
                    {typhoon.status === 1 ? "🟢 活跃" : "⚪ 已停止"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 右侧地图容器 */}
      <div
        style={{
          flex: 1,
          position: "relative",
          borderRadius: "10px",
          overflow: "hidden",
          minHeight: "800px", // 增加最小高度到800px，确保地图容器足够大
        }}
      >
        {/* 地图 */}
        <MapContainer
          center={[25, 125]}
          zoom={5}
          minZoom={3}
          maxZoom={18}
          style={{ width: "100%", height: "100%", zIndex: 1 }}
          ref={mapRef}
        >
          {/* 使用高德地图瓦片服务（国内访问稳定） */}
          <TileLayer
            attribution='&copy; <a href="https://www.amap.com/">高德地图</a>'
            url="https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}"
            subdomains={["1", "2", "3", "4"]}
            maxZoom={18}
            minZoom={3}
          />

          {/* 渲染台风路径 */}
          {Array.from(pathsData.entries()).map(([typhoonId, pathPoints]) => {
            if (!pathPoints || pathPoints.length === 0) return null;

            // 获取路径坐标
            const pathCoordinates = pathPoints.map((point) => [
              point.latitude,
              point.longitude,
            ]);

            // 获取第一个点的强度作为路径颜色
            const pathColor = getColorByIntensity(pathPoints[0]?.intensity);

            return (
              <React.Fragment key={typhoonId}>
                {/* 路径线 */}
                <Polyline
                  positions={pathCoordinates}
                  color={pathColor}
                  weight={3}
                  opacity={0.7}
                />

                {/* 路径点 - 使用Tooltip实现悬浮显示 */}
                {pathPoints.map((point, index) => {
                  // 修复字段名映射
                  const windSpeed = point.max_wind_speed || point.wind_speed;

                  return (
                    <CircleMarker
                      key={`${typhoonId}-${index}`}
                      center={[point.latitude, point.longitude]}
                      radius={getRadiusByWindSpeed(windSpeed)}
                      fillColor={getColorByIntensity(point.intensity)}
                      color="white"
                      weight={2}
                      opacity={1}
                      fillOpacity={0.8}
                    >
                      <Tooltip direction="top" offset={[0, -10]} opacity={0.95}>
                        {createPopupContent(point)}
                      </Tooltip>
                    </CircleMarker>
                  );
                })}
              </React.Fragment>
            );
          })}
        </MapContainer>

        {/* 加载提示 */}
        {pathLoading && (
          <div
            style={{
              position: "absolute",
              top: "10px",
              right: "10px",
              background: "white",
              padding: "10px 15px",
              borderRadius: "8px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
              zIndex: 1000,
            }}
          >
            ⏳ 加载路径数据中...
          </div>
        )}

        {/* 错误提示 */}
        {pathError && (
          <div
            style={{
              position: "absolute",
              top: "10px",
              right: "10px",
              background: "#fee",
              color: "#c00",
              padding: "10px 15px",
              borderRadius: "8px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
              zIndex: 1000,
            }}
          >
            ❌ {pathError}
          </div>
        )}

        {/* 图例面板 */}
        {selectedTyphoons && selectedTyphoons.size > 0 && (
          <div
            style={{
              position: "absolute",
              top: "20px",
              right: "20px",
              background: "white",
              padding: "15px",
              borderRadius: "10px",
              boxShadow: "0 4px 15px rgba(0,0,0,0.15)",
              maxWidth: "250px",
              zIndex: 1000,
            }}
          >
            <div style={{ marginBottom: "10px" }}>
              <h4 style={{ fontSize: "14px", color: "#333", margin: 0 }}>
                图例
              </h4>
            </div>
            <div
              style={{ display: "flex", flexDirection: "column", gap: "12px" }}
            >
              {/* 强度等级 */}
              <div
                style={{ display: "flex", flexDirection: "column", gap: "5px" }}
              >
                <div
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "#666",
                    marginBottom: "3px",
                  }}
                >
                  强度等级
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "12px",
                    color: "#555",
                  }}
                >
                  <div
                    style={{
                      width: "20px",
                      height: "3px",
                      background: "#3498db",
                      borderRadius: "2px",
                    }}
                  ></div>
                  <span>热带低压 (TD)</span>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "12px",
                    color: "#555",
                  }}
                >
                  <div
                    style={{
                      width: "20px",
                      height: "3px",
                      background: "#2ecc71",
                      borderRadius: "2px",
                    }}
                  ></div>
                  <span>热带风暴 (TS)</span>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "12px",
                    color: "#555",
                  }}
                >
                  <div
                    style={{
                      width: "20px",
                      height: "3px",
                      background: "#f1c40f",
                      borderRadius: "2px",
                    }}
                  ></div>
                  <span>强热带风暴 (STS)</span>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "12px",
                    color: "#555",
                  }}
                >
                  <div
                    style={{
                      width: "20px",
                      height: "3px",
                      background: "#e67e22",
                      borderRadius: "2px",
                    }}
                  ></div>
                  <span>台风 (TY)</span>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "12px",
                    color: "#555",
                  }}
                >
                  <div
                    style={{
                      width: "20px",
                      height: "3px",
                      background: "#e74c3c",
                      borderRadius: "2px",
                    }}
                  ></div>
                  <span>强台风 (STY)</span>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "12px",
                    color: "#555",
                  }}
                >
                  <div
                    style={{
                      width: "20px",
                      height: "3px",
                      background: "#c0392b",
                      borderRadius: "2px",
                    }}
                  ></div>
                  <span>超强台风 (SuperTY)</span>
                </div>
              </div>

              {/* 轨迹点大小 */}
              <div
                style={{ display: "flex", flexDirection: "column", gap: "5px" }}
              >
                <div
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "#666",
                    marginBottom: "3px",
                  }}
                >
                  轨迹点大小
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "12px",
                    color: "#555",
                  }}
                >
                  <div
                    style={{
                      width: "8px",
                      height: "8px",
                      background: "#667eea",
                      borderRadius: "50%",
                      border: "2px solid white",
                      boxShadow: "0 0 3px rgba(0,0,0,0.3)",
                    }}
                  ></div>
                  <span>风速较小 (~10m/s)</span>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "12px",
                    color: "#555",
                  }}
                >
                  <div
                    style={{
                      width: "14px",
                      height: "14px",
                      background: "#667eea",
                      borderRadius: "50%",
                      border: "2px solid white",
                      boxShadow: "0 0 3px rgba(0,0,0,0.3)",
                    }}
                  ></div>
                  <span>风速较大 (~50m/s)</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default MapVisualization;
