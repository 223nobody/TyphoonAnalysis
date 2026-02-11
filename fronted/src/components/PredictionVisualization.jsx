/**
 * 预测可视化组件 - 基于MapVisualization扩展
 * 功能：点击台风路径上的任意数据点，触发并可视化展示该点位未来24小时的精细化预测路径
 */
import React, { useState, useEffect, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Tooltip,
  useMap,
  Polygon,
  Marker,
} from "react-leaflet";
import { useSearchParams } from "react-router-dom";
import L from "leaflet";
import { message } from "antd";
import {
  getTyphoonList,
  getTyphoonPath,
  getTyphoonForecast,
  getCollectTyphoons,
  addCollectTyphoon,
  removeCollectTyphoon,
  searchTyphoons,
  predictFromArbitraryStart,
} from "../services/api";
import "leaflet/dist/leaflet.css";
import "../styles/MapVisualization.css";
import "../styles/common.css";
import taifengIcon from "../pictures/taifeng.gif";
import nocollectIcon from "../pictures/nocollect.svg";
import iscollectIcon from "../pictures/iscollect.svg";

/**
 * 经度归一化工具函数（仅用于显示）
 * 将任意经度值归一化到 [-180°, 180°] 范围，用于 Tooltip 显示
 * 注意：地图坐标不使用此函数，直接使用原始经度值
 */
const normalizeLongitudeForDisplay = (lng) => {
  if (typeof lng !== "number" || isNaN(lng)) return lng;
  const normalized = ((lng + 180) % 360) - 180;
  return normalized === 180 ? -180 : normalized;
};

// 创建台风眼图标
const createTyphoonIcon = () => {
  return L.icon({
    iconUrl: taifengIcon,
    iconSize: [40, 40],
    iconAnchor: [20, 20],
    popupAnchor: [0, -20],
  });
};

// 创建预测点图标
const createPredictionIcon = () => {
  return L.divIcon({
    className: "prediction-point-icon",
    html: `<div style="
      width: 16px;
      height: 16px;
      background: linear-gradient(135deg, #ff6b6b 0%, #ff8e8e 100%);
      border: 3px solid white;
      border-radius: 50%;
      box-shadow: 0 0 10px rgba(255, 107, 107, 0.6);
      animation: pulse 2s infinite;
    "></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
};

// 创建警戒线文字标注图标 - 竖排显示
const createWarningLineLabel = (text, color) => {
  const chars = text.split("");
  const charsHtml = chars.map((char) => `<div>${char}</div>`).join("");

  return L.divIcon({
    className: "warning-line-label",
    html: `<div style="
      display: flex;
      flex-direction: column;
      align-items: center;
      font-size: 10px;
      font-weight: bold;
      color: ${color};
      text-shadow:
        -1px -1px 0 rgba(255, 255, 255, 0.8),
        1px -1px 0 rgba(255, 255, 255, 0.8),
        -1px 1px 0 rgba(255, 255, 255, 0.8),
        1px 1px 0 rgba(255, 255, 255, 0.8),
        0 0 3px rgba(255, 255, 255, 0.9);
      line-height: 1.3;
      letter-spacing: 2px;
    ">${charsHtml}</div>`,
    iconSize: [24, 120],
    iconAnchor: [12, 60],
  });
};

// 生成不规则风圈 - 西北象限半径放大
const generateIrregularWindCircle = (center, baseRadius, windLevel) => {
  const [lat, lng] = center;
  const points = [];
  const numPoints = 1800;
  const northwestRadiusMultiplier = 1.5;

  for (let i = 0; i <= numPoints; i++) {
    const angle = (i * 360) / numPoints;
    const radian = (angle * Math.PI) / 180;

    let radiusMultiplier;
    if (angle > 90 && angle < 180) {
      radiusMultiplier = northwestRadiusMultiplier;
    } else {
      radiusMultiplier = 1.0;
    }

    const radius = baseRadius * radiusMultiplier;
    const latOffset = (radius / 111) * Math.sin(radian);
    const lngOffset =
      (radius / (111 * Math.cos((lat * Math.PI) / 180))) * Math.cos(radian);

    points.push([lat + latOffset, lng + lngOffset]);
  }

  return points;
};

// 地图控制器组件
function MapController({ center, zoom, onZoomChange, onMouseMove }) {
  const map = useMap();

  useEffect(() => {
    if (center && center.length === 2 && zoom) {
      map.setView(center, zoom, {
        animate: true,
        duration: 1.0,
      });
    }
  }, [center, zoom, map]);

  useEffect(() => {
    const handleZoomEnd = () => {
      const currentZoom = map.getZoom();
      if (onZoomChange) {
        onZoomChange(currentZoom);
      }
    };

    map.on("zoomend", handleZoomEnd);
    const initialZoom = map.getZoom();
    if (onZoomChange) {
      onZoomChange(initialZoom);
    }

    return () => {
      map.off("zoomend", handleZoomEnd);
    };
  }, [map, onZoomChange]);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (onMouseMove) {
        onMouseMove({
          lat: e.latlng.lat,
          lng: e.latlng.lng,
        });
      }
    };

    const handleMouseOut = () => {
      if (onMouseMove) {
        onMouseMove(null);
      }
    };

    map.on("mousemove", handleMouseMove);
    map.on("mouseout", handleMouseOut);

    return () => {
      map.off("mousemove", handleMouseMove);
      map.off("mouseout", handleMouseOut);
    };
  }, [map, onMouseMove]);

  return null;
}

function PredictionVisualization({
  selectedTyphoons,
  onTyphoonSelect,
  allowMultipleTyphoons,
  setAllowMultipleTyphoons,
  clearAllSelectedTyphoons,
}) {
  const [searchParams] = useSearchParams();
  const urlTyphoonId = searchParams.get("typhoon_id");

  // 台风列表相关状态
  const [typhoons, setTyphoons] = useState([]);
  const [filteredTyphoons, setFilteredTyphoons] = useState([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState(null);
  const [isSearching, setIsSearching] = useState(false);

  // 筛选条件
  const [filters, setFilters] = useState({
    year: "2026",
    status: "",
    search: "",
  });

  // 地图路径相关状态
  const [pathsData, setPathsData] = useState(new Map());
  const [pathLoading, setPathLoading] = useState(false);
  const [pathError, setPathError] = useState(null);
  const mapRef = useRef(null);

  // 预测路径数据状态
  const [forecastData, setForecastData] = useState(new Map());
  const [forecastLoading, setForecastLoading] = useState(false);
  const [showForecast, setShowForecast] = useState(true);

  // 地图图层状态
  const [mapLayer, setMapLayer] = useState("terrain");

  // 地图中心和缩放状态
  const [mapCenter, setMapCenter] = useState([23.5, 120.0]);
  const [mapZoom, setMapZoom] = useState(3);

  // 跟踪上一次选中的台风集合
  const [prevSelectedTyphoons, setPrevSelectedTyphoons] = useState(new Set());
  const [latestVisualizedTyphoon, setLatestVisualizedTyphoon] = useState(null);

  // 鼠标位置经纬度状态
  const [mousePosition, setMousePosition] = useState(null);

  // 收藏相关状态
  const [collectTyphoons, setCollectTyphoons] = useState([]);
  const [isCollecting, setIsCollecting] = useState(false);

  // ===== 预测可视化新增状态 =====
  const [selectedPoint, setSelectedPoint] = useState(null);
  const [predictionData, setPredictionData] = useState(null);
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [predictionError, setPredictionError] = useState(null);
  const [showPredictionPanel, setShowPredictionPanel] = useState(false);

  // 使用ref跟踪是否已经处理过URL参数
  const hasProcessedUrlTyphoonId = useRef(false);
  const hasTriedYearSwitch = useRef(false);

  // 处理URL参数中的typhoon_id - 第一阶段：提取年份并切换
  useEffect(() => {
    if (urlTyphoonId && !hasProcessedUrlTyphoonId.current) {
      if (!urlTyphoonId || urlTyphoonId.trim() === "") {
        message.error("台风ID格式错误");
        hasProcessedUrlTyphoonId.current = true;
        return;
      }

      const typhoonIdStr = String(urlTyphoonId);
      let targetYear = null;

      if (typhoonIdStr.length >= 2) {
        const yearPrefix = typhoonIdStr.substring(0, 2);
        targetYear = parseInt("20" + yearPrefix);

        if (!isNaN(targetYear) && targetYear >= 2000 && targetYear <= 2099) {
          if (filters.year !== targetYear.toString()) {
            setFilters((prev) => ({ ...prev, year: targetYear.toString() }));
            hasTriedYearSwitch.current = true;
          }
        }
      }
    }
  }, [urlTyphoonId, filters.year]);

  // 处理URL参数中的typhoon_id - 第二阶段：在数据加载完成后选中台风
  useEffect(() => {
    if (
      urlTyphoonId &&
      !hasProcessedUrlTyphoonId.current &&
      !listLoading &&
      typhoons.length > 0
    ) {
      const typhoonExists = typhoons.some((t) => t.typhoon_id === urlTyphoonId);

      if (typhoonExists) {
        if (onTyphoonSelect) {
          if (!selectedTyphoons.has(urlTyphoonId)) {
            onTyphoonSelect(urlTyphoonId);
          }
          hasProcessedUrlTyphoonId.current = true;
        }
      } else {
        if (hasTriedYearSwitch.current) {
          message.warning(`台风 ${urlTyphoonId} 在当前年份列表中未找到`);
          hasProcessedUrlTyphoonId.current = true;
        }
      }
    }
  }, [urlTyphoonId, typhoons, listLoading, onTyphoonSelect, selectedTyphoons, filters.year]);

  // 当URL参数变化时，重置处理标志
  useEffect(() => {
    hasProcessedUrlTyphoonId.current = false;
    hasTriedYearSwitch.current = false;
  }, [urlTyphoonId]);

  // 加载台风列表
  useEffect(() => {
    loadTyphoons();
    loadCollectTyphoons();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.year, filters.status]);

  // 搜索功能 - 使用防抖处理
  useEffect(() => {
    const timer = setTimeout(() => {
      if (filters.search && filters.search.trim() !== "") {
        handleSearch();
      } else {
        setFilteredTyphoons(typhoons);
      }
    }, 300);

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.search]);

  // 当选中的台风变化时，加载路径数据并定位地图
  useEffect(() => {
    if (selectedTyphoons && selectedTyphoons.size > 0) {
      loadTyphoonPaths();

      const newlySelected = Array.from(selectedTyphoons).find(
        (id) => !prevSelectedTyphoons.has(id)
      );

      if (newlySelected) {
        const typhoon = typhoons.find((t) => t.typhoon_id === newlySelected);
        if (typhoon) {
          centerMapOnTyphoon(newlySelected);
        }
        setLatestVisualizedTyphoon(newlySelected);
      }

      setPrevSelectedTyphoons(new Set(selectedTyphoons));
    } else {
      setPathsData(new Map());
      setForecastData(new Map());
      setPrevSelectedTyphoons(new Set());
      setLatestVisualizedTyphoon(null);
      // 清除预测数据
      setPredictionData(null);
      setSelectedPoint(null);
      setShowPredictionPanel(false);
    }
  }, [selectedTyphoons, typhoons]);

  // 加载台风列表
  const loadTyphoons = async () => {
    try {
      setListLoading(true);
      setListError(null);

      const params = {
        limit: 100,
      };

      if (filters.year) {
        params.year = parseInt(filters.year);
      }

      if (filters.status !== "") {
        params.status = parseInt(filters.status);
      }

      const data = await getTyphoonList(params);

      if (data && data.items && Array.isArray(data.items)) {
        setTyphoons(data.items);
        if (!filters.search || filters.search.trim() === "") {
          setFilteredTyphoons(data.items);
        }
      } else if (data && Array.isArray(data)) {
        setTyphoons(data);
        if (!filters.search || filters.search.trim() === "") {
          setFilteredTyphoons(data);
        }
      } else {
        setListError("加载台风列表失败：数据格式错误");
      }
    } catch (err) {
      setListError(err.message || "加载失败，请检查后端服务是否正常运行");
    } finally {
      setListLoading(false);
    }
  };

  // 搜索台风
  const handleSearch = async () => {
    const searchTerm = filters.search.trim();
    if (!searchTerm) {
      setFilteredTyphoons(typhoons);
      return;
    }

    try {
      setIsSearching(true);
      const params = {
        keyword: searchTerm,
        limit: 100,
      };

      const data = await searchTyphoons(params);

      if (data && data.items && Array.isArray(data.items)) {
        setFilteredTyphoons(data.items);
      } else if (data && Array.isArray(data)) {
        setFilteredTyphoons(data);
      } else {
        setFilteredTyphoons([]);
      }
    } catch (err) {
      message.error("搜索失败: " + (err.message || "请稍后重试"));
      setFilteredTyphoons([]);
    } finally {
      setIsSearching(false);
    }
  };

  // 加载收藏列表
  const loadCollectTyphoons = async () => {
    try {
      const data = await getCollectTyphoons();
      const collectIds = data.map((t) => t.typhoon_id);
      setCollectTyphoons(collectIds);
    } catch (err) {
      console.error("加载收藏列表失败:", err);
    }
  };

  // 处理收藏/取消收藏
  const handleToggleCollect = async (typhoonId, typhoonName, event) => {
    event.stopPropagation();

    try {
      setIsCollecting(true);
      const isCollected = collectTyphoons.includes(typhoonId);

      if (isCollected) {
        await removeCollectTyphoon(typhoonId);
        setCollectTyphoons(collectTyphoons.filter((id) => id !== typhoonId));
        message.success("已取消收藏");
      } else {
        await addCollectTyphoon(typhoonId, typhoonName);
        setCollectTyphoons([...collectTyphoons, typhoonId]);
        message.success("收藏成功");
      }
    } catch (err) {
      message.error(err.message || "操作失败");
    } finally {
      setIsCollecting(false);
    }
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
          }
        } catch (err) {
          console.error(`加载台风 ${typhoonId} 路径失败:`, err);
        }
      }

      setPathsData(newPathsData);
      loadForecastPaths();
    } catch (err) {
      setPathError(err.message || "加载失败，请稍后重试");
    } finally {
      setPathLoading(false);
    }
  };

  // 加载预测路径数据
  const loadForecastPaths = async () => {
    try {
      setForecastLoading(true);
      const newForecastData = new Map();

      for (const typhoonId of selectedTyphoons) {
        try {
          const typhoonInfo = typhoons.find((t) => t.typhoon_id === typhoonId);

          if (!typhoonInfo || typhoonInfo.status !== 1) {
            continue;
          }

          const data = await getTyphoonForecast(typhoonId);
          if (data && Array.isArray(data) && data.length > 0) {
            newForecastData.set(typhoonId, data);
          }
        } catch (err) {
          console.error(`加载台风 ${typhoonId} 预测路径失败:`, err);
        }
      }

      setForecastData(newForecastData);
    } catch (err) {
      console.error("加载预测路径失败:", err);
    } finally {
      setForecastLoading(false);
    }
  };

  // ===== 核心功能：点击路径点触发预测 =====
  const handlePathPointClick = async (point, typhoonId) => {
    try {
      setPredictionLoading(true);
      setPredictionError(null);
      setSelectedPoint({ ...point, typhoonId });

      // 调用任意起点预测API
      const startTime = new Date(point.timestamp || point.record_time);
      const startTimeStr = startTime.toISOString();

      const response = await predictFromArbitraryStart(
        typhoonId,
        startTimeStr,
        parseFloat(point.latitude),
        parseFloat(point.longitude),
        point.center_pressure || null,
        point.max_wind_speed || null,
        24 // 24小时预测
      );

      setPredictionData(response);
      setShowPredictionPanel(true);
      message.success(`已生成从 ${startTime.toLocaleString("zh-CN")} 开始的24小时预测`);
    } catch (err) {
      console.error("预测失败:", err);
      setPredictionError(err.message || "预测失败，请稍后重试");
      message.error("预测失败: " + (err.message || "请稍后重试"));
    } finally {
      setPredictionLoading(false);
    }
  };

  // 处理台风选择
  const handleTyphoonClick = (typhoonId) => {
    if (onTyphoonSelect) {
      onTyphoonSelect(typhoonId);
    }
  };

  // 处理多台风叠加显示切换
  const handleAllowMultipleChange = (e) => {
    const newValue = e.target.checked;

    if (allowMultipleTyphoons && !newValue && selectedTyphoons.size > 0) {
      clearAllSelectedTyphoons();
    }

    setAllowMultipleTyphoons(newValue);
  };

  // 将地图中心定位到指定台风
  const centerMapOnTyphoon = async (typhoonId) => {
    try {
      const pathData = await getTyphoonPath(typhoonId);
      if (
        pathData &&
        pathData.items &&
        Array.isArray(pathData.items) &&
        pathData.items.length > 0
      ) {
        const latestPoint = pathData.items[pathData.items.length - 1];

        if (latestPoint && latestPoint.latitude && latestPoint.longitude) {
          const lat = parseFloat(latestPoint.latitude);
          const lng = parseFloat(latestPoint.longitude);

          setMapCenter([lat, lng]);
          setMapZoom(5);
        }
      }
    } catch (error) {
      console.error(`定位台风 ${typhoonId} 失败:`, error);
    }
  };

  // 获取年份列表
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

  // 根据风速获取半径
  const getRadiusByWindSpeed = (windSpeed) => {
    if (!windSpeed) return 4;
    if (windSpeed < 20) return 4;
    if (windSpeed < 30) return 6;
    if (windSpeed < 40) return 8;
    if (windSpeed < 50) return 10;
    return 12;
  };

  // 创建弹窗内容
  const createPopupContent = (point) => {
    const timestamp = point.timestamp || point.record_time || point.time;
    const windSpeed = point.max_wind_speed || point.wind_speed;
    const pressure = point.center_pressure || point.pressure;
    const movingSpeed = point.moving_speed;
    const movingDirection = point.moving_direction;

    const normalizedLng = normalizeLongitudeForDisplay(point.longitude);
    const lngDirection = normalizedLng >= 0 ? "东经" : "西经";
    const lngValue = Math.abs(normalizedLng);

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
          <strong>位置：</strong>北纬 {point.latitude?.toFixed(2)}°，
          {lngDirection} {lngValue?.toFixed(2)}°
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
        <div
          style={{
            marginTop: "10px",
            padding: "8px",
            background: "#f0f4ff",
            borderRadius: "4px",
            fontSize: "12px",
            color: "#667eea",
            textAlign: "center",
            cursor: "pointer",
          }}
        >
          💡 点击此点可查看24小时预测
        </div>
      </div>
    );
  };

  // 获取强度等级
  const getIntensityLevel = (windSpeed, pressure) => {
    if (!windSpeed) return "未知";
    if (windSpeed >= 51) return "超强台风";
    if (windSpeed >= 41) return "强台风";
    if (windSpeed >= 32) return "台风";
    if (windSpeed >= 24) return "强热带风暴";
    if (windSpeed >= 17) return "热带风暴";
    return "热带低压";
  };

  // 获取置信度颜色
  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.7) return "#22c55e";
    if (confidence >= 0.5) return "#eab308";
    return "#ef4444";
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
                onChange={handleAllowMultipleChange}
                style={{
                  marginRight: "8px",
                  width: "16px",
                  height: "16px",
                  cursor: "pointer",
                }}
              />
              <span style={{ fontWeight: "500" }}>多台风叠加显示</span>
            </label>
          </div>
        </div>

        {/* 加载状态 */}
        {(listLoading || isSearching) && (
          <div
            style={{ textAlign: "center", padding: "20px", color: "#6b7280" }}
          >
            {isSearching ? "🔍 正在搜索..." : "正在加载台风数据..."}
          </div>
        )}

        {/* 错误提示 */}
        {listError && (
          <div className="error-message" style={{ marginBottom: "15px" }}>
            ❌ {listError}
          </div>
        )}

        {/* 台风列表 */}
        {!listLoading && !listError && !isSearching && (
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
              {filteredTyphoons.map((typhoon) => {
                const isCollected = collectTyphoons.includes(
                  typhoon.typhoon_id
                );
                const isSelected =
                  selectedTyphoons && selectedTyphoons.has(typhoon.typhoon_id);
                const typhoonName =
                  typhoon.typhoon_name_cn || typhoon.typhoon_name;
                return (
                  <div
                    key={typhoon.typhoon_id}
                    onClick={() => handleTyphoonClick(typhoon.typhoon_id)}
                    style={{
                      padding: "12px",
                      background: isSelected
                        ? "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
                        : "white",
                      color: isSelected ? "white" : "#1f2937",
                      borderRadius: "8px",
                      cursor: "pointer",
                      transition: "all 0.3s ease",
                      border: "1px solid #e5e7eb",
                      position: "relative",
                    }}
                  >
                    <img
                      src={isCollected ? iscollectIcon : nocollectIcon}
                      alt={isCollected ? "已收藏" : "收藏"}
                      onClick={(e) =>
                        handleToggleCollect(typhoon.typhoon_id, typhoonName, e)
                      }
                      style={{
                        position: "absolute",
                        top: "10px",
                        right: "10px",
                        width: "18px",
                        height: "18px",
                        cursor: "pointer",
                      }}
                    />
                    <div
                      style={{
                        fontWeight: "bold",
                        marginBottom: "5px",
                        paddingRight: "45px",
                      }}
                    >
                      {typhoon.typhoon_name_cn ||
                        typhoon.typhoon_name ||
                        typhoon.typhoon_id}
                    </div>
                    <div style={{ fontSize: "12px", opacity: 0.9 }}>
                      ID: {typhoon.typhoon_id} | {typhoon.year}年 |{" "}
                      {typhoon.status === 1 ? "🟢 活跃" : "⚪ 已停止"}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* 中间地图容器 */}
      <div
        style={{
          flex: 1,
          position: "relative",
          borderRadius: "10px",
          overflow: "hidden",
          minHeight: "800px",
        }}
      >
        {/* 地图 */}
        <MapContainer
          center={[30, 100]}
          zoom={1.5}
          minZoom={1}
          maxZoom={18}
          style={{ width: "100%", height: "100%", zIndex: 1 }}
          ref={mapRef}
        >
          <MapController
            center={mapCenter}
            zoom={mapZoom}
            onZoomChange={setMapZoom}
            onMouseMove={setMousePosition}
          />

          {/* 地图图层 */}
          {mapLayer === "terrain" ? (
            <>
              <TileLayer
                key="amap-global"
                attribution='&copy; <a href="https://www.amap.com/">高德地图</a>'
                url="https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7&x={x}&y={y}&z={z}"
                subdomains={["1", "2", "3", "4"]}
                maxZoom={18}
                minZoom={2}
              />
            </>
          ) : (
            <>
              <TileLayer
                key="tianditu-satellite"
                attribution='&copy; <a href="http://www.tianditu.gov.cn/">天地图</a>'
                url="http://t{s}.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=eb771030fd9565381964c832ef07698a"
                subdomains={["0", "1", "2", "3", "4", "5", "6", "7"]}
                maxZoom={18}
                minZoom={2}
              />
              <TileLayer
                key="tianditu-labels"
                url="http://t{s}.tianditu.gov.cn/cia_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cia&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=eb771030fd9565381964c832ef07698a"
                subdomains={["0", "1", "2", "3", "4", "5", "6", "7"]}
                maxZoom={18}
                minZoom={2}
                opacity={0.9}
              />
            </>
          )}

          {/* 48小时警戒线 */}
          <Polyline
            positions={[
              [0, 105],
              [0, 120],
              [15, 132],
              [34, 132],
            ]}
            color="#FF0000"
            weight={1}
            dashArray="5, 5"
            opacity={0.8}
          />
          <Marker
            position={[28, 132]}
            icon={createWarningLineLabel("48小时警戒线", "#0000FF")}
          />

          {/* 24小时警戒线 */}
          <Polyline
            positions={[
              [0, 105],
              [4.5, 113],
              [4.5, 113],
              [11, 119],
              [11, 119],
              [18, 119],
              [18, 119],
              [22, 127],
              [22, 127],
              [34, 127],
            ]}
            color="#FFFF00"
            weight={3}
            dashArray="5, 5"
            opacity={0.9}
          />
          <Marker
            position={[28, 127]}
            icon={createWarningLineLabel("24小时警戒线", "#FFB85C")}
          />

          {/* 渲染台风路径 */}
          {Array.from(pathsData.entries()).map(([typhoonId, pathPoints]) => {
            if (!pathPoints || pathPoints.length === 0) return null;

            const pathCoordinates = pathPoints.map((point) => [
              point.latitude,
              point.longitude,
            ]);

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

                {/* 路径点 - 可点击触发预测 */}
                {pathPoints.map((point, index) => {
                  const windSpeed = point.max_wind_speed || point.wind_speed;
                  const isLatestPoint = index === pathPoints.length - 1;

                  return (
                    <React.Fragment key={`${typhoonId}-${index}`}>
                      <CircleMarker
                        center={[point.latitude, point.longitude]}
                        radius={getRadiusByWindSpeed(windSpeed)}
                        fillColor={getColorByIntensity(point.intensity)}
                        color="white"
                        weight={2}
                        opacity={1}
                        fillOpacity={0.8}
                        eventHandlers={{
                          click: () => handlePathPointClick(point, typhoonId),
                        }}
                        style={{ cursor: "pointer" }}
                      >
                        <Tooltip
                          direction="top"
                          offset={[0, -10]}
                          opacity={0.95}
                        >
                          {createPopupContent(point)}
                        </Tooltip>
                      </CircleMarker>

                      {/* 风圈可视化 */}
                      {isLatestPoint && (
                        <>
                          <Polygon
                            positions={generateIrregularWindCircle(
                              [point.latitude, point.longitude],
                              120,
                              7
                            )}
                            pathOptions={{
                              fillColor: "rgba(200, 200, 200, 0.45)",
                              color: "#aaa",
                              weight: 2,
                              fillOpacity: 0.45,
                            }}
                          />
                          <Polygon
                            positions={generateIrregularWindCircle(
                              [point.latitude, point.longitude],
                              65,
                              10
                            )}
                            pathOptions={{
                              fillColor: "rgba(255, 165, 0, 0.35)",
                              color: "rgba(255, 165, 0, 0.6)",
                              weight: 2,
                              fillOpacity: 0.35,
                            }}
                          />
                          <Polygon
                            positions={generateIrregularWindCircle(
                              [point.latitude, point.longitude],
                              30,
                              12
                            )}
                            pathOptions={{
                              fillColor: "rgba(255, 255, 0, 0.4)",
                              color: "rgba(255, 255, 0, 0.7)",
                              weight: 2.5,
                              fillOpacity: 0.4,
                            }}
                          />
                          <Marker
                            position={[point.latitude, point.longitude]}
                            icon={createTyphoonIcon()}
                          >
                            <Tooltip
                              direction="top"
                              offset={[0, -30]}
                              opacity={0.95}
                            >
                              <div>
                                {createPopupContent(point)}
                                <div
                                  style={{
                                    marginTop: "10px",
                                    paddingTop: "10px",
                                    borderTop: "1px solid #e0e0e0",
                                    fontSize: "12px",
                                    fontWeight: "bold",
                                    color: "#667eea",
                                    textAlign: "center",
                                  }}
                                >
                                  台风眼中心
                                </div>
                              </div>
                            </Tooltip>
                          </Marker>
                        </>
                      )}
                    </React.Fragment>
                  );
                })}
              </React.Fragment>
            );
          })}

          {/* 渲染预测路径 */}
          {predictionData && predictionData.length > 0 && selectedPoint && (
            <React.Fragment key="ai-prediction">
              {/* 连接线：实际台风节点(预测起点)与第一个预测路径点 */}
              <Polyline
                positions={[
                  [selectedPoint.latitude, selectedPoint.longitude],
                  [predictionData[0].predicted_latitude, predictionData[0].predicted_longitude],
                ]}
                color="#ff6b6b"
                weight={3}
                opacity={0.8}
                dashArray="8, 4"
              />

              {/* 预测路径线：预测点之间用红色虚线相连 */}
              <Polyline
                positions={predictionData.map((p) => [
                  p.predicted_latitude,
                  p.predicted_longitude,
                ])}
                color="#ff6b6b"
                weight={3}
                opacity={0.8}
                dashArray="8, 4"
              />

              {/* 预测路径点 - 使用图例规范的颜色和大小 */}
              {predictionData.map((point, index) => {
                // 根据预测风速获取强度等级和对应颜色
                const intensity = getIntensityLevel(
                  point.predicted_wind_speed,
                  point.predicted_pressure
                );
                const pointColor = getColorByIntensity(intensity);
                const pointRadius = getRadiusByWindSpeed(point.predicted_wind_speed);

                return (
                  <CircleMarker
                    key={`prediction-${index}`}
                    center={[point.predicted_latitude, point.predicted_longitude]}
                    radius={pointRadius}
                    fillColor={pointColor}
                    color="white"
                    weight={2}
                    opacity={1}
                    fillOpacity={0.8}
                  >
                    <Tooltip direction="top" offset={[0, -10]} opacity={0.95}>
                      <div
                        style={{
                          minWidth: "180px",
                          fontSize: "12px",
                          lineHeight: "1.5",
                        }}
                      >
                        <div
                          style={{
                            background: pointColor,
                            color: "white",
                            padding: "4px 8px",
                            borderRadius: "4px",
                            marginBottom: "8px",
                            fontWeight: "bold",
                            textAlign: "center",
                          }}
                        >
                          🤖 预测点 {index + 1}/{predictionData.length}
                        </div>
                        <p style={{ margin: "4px 0" }}>
                          <strong>预报时间：</strong>
                          {new Date(point.forecast_time).toLocaleString("zh-CN")}
                        </p>
                        <p style={{ margin: "4px 0" }}>
                          <strong>位置：</strong>
                          {point.predicted_latitude?.toFixed(2)}°N,{" "}
                          {point.predicted_longitude?.toFixed(2)}°E
                        </p>
                        <p style={{ margin: "4px 0" }}>
                          <strong>中心气压：</strong>
                          {point.predicted_pressure?.toFixed(0)} hPa
                        </p>
                        <p style={{ margin: "4px 0" }}>
                          <strong>最大风速：</strong>
                          {point.predicted_wind_speed?.toFixed(1)} m/s
                        </p>
                        <p style={{ margin: "4px 0" }}>
                          <strong>强度等级：</strong>
                          <span
                            style={{
                              padding: "2px 6px",
                              borderRadius: "3px",
                              background:
                                point.predicted_wind_speed >= 32
                                  ? "#fee2e2"
                                  : "#fef3c7",
                              color:
                                point.predicted_wind_speed >= 32
                                  ? "#dc2626"
                                  : "#d97706",
                              fontWeight: "bold",
                              fontSize: "11px",
                            }}
                          >
                            {intensity}
                          </span>
                        </p>
                        <p style={{ margin: "4px 0" }}>
                          <strong>置信度：</strong>
                          <span
                            style={{
                              color: getConfidenceColor(point.confidence),
                              fontWeight: "bold",
                            }}
                          >
                            {(point.confidence * 100).toFixed(1)}%
                          </span>
                        </p>
                      </div>
                    </Tooltip>
                  </CircleMarker>
                );
              })}

              {/* 预测起点标记 */}
              <Marker
                position={[selectedPoint.latitude, selectedPoint.longitude]}
                icon={createPredictionIcon()}
              >
                <Tooltip direction="top" offset={[0, -20]} opacity={0.95}>
                  <div
                    style={{
                      fontSize: "12px",
                      textAlign: "center",
                      fontWeight: "bold",
                      color: "#ff6b6b",
                    }}
                  >
                    🔴 预测起点
                    <br />
                    {new Date(
                      selectedPoint.timestamp || selectedPoint.record_time
                    ).toLocaleString("zh-CN")}
                  </div>
                </Tooltip>
              </Marker>
            </React.Fragment>
          )}

          {/* 渲染机构预测路径 */}
          {showForecast &&
            Array.from(forecastData.entries()).map(
              ([typhoonId, agencyForecasts]) => {
                if (!agencyForecasts || agencyForecasts.length === 0)
                  return null;

                return (
                  <React.Fragment key={`forecast-${typhoonId}`}>
                    {agencyForecasts.map((agencyForecast) => {
                      const { agency, color, points } = agencyForecast;

                      if (!points || points.length === 0) return null;

                      const historicalPath = pathsData.get(typhoonId);
                      let fullForecastPath = [...points];
                      if (historicalPath && historicalPath.length > 0) {
                        const lastHistoricalPoint =
                          historicalPath[historicalPath.length - 1];
                        fullForecastPath.unshift(lastHistoricalPoint);
                      }

                      const forecastCoordinates = fullForecastPath.map(
                        (point) => [point.latitude, point.longitude]
                      );

                      return (
                        <React.Fragment key={`forecast-${typhoonId}-${agency}`}>
                          <Polyline
                            positions={forecastCoordinates}
                            color={color}
                            weight={2}
                            opacity={0.7}
                            dashArray="5, 10"
                          />

                          {points.map((point, index) => {
                            const normalizedLng = normalizeLongitudeForDisplay(
                              point.longitude
                            );

                            return (
                              <CircleMarker
                                key={`forecast-${typhoonId}-${agency}-${index}`}
                                center={[point.latitude, point.longitude]}
                                radius={4}
                                fillColor={color}
                                color="white"
                                weight={1}
                                opacity={0.8}
                                fillOpacity={0.6}
                              >
                                <Tooltip
                                  direction="top"
                                  offset={[0, -10]}
                                  opacity={0.9}
                                >
                                  <div
                                    style={{
                                      background: color,
                                      color: "white",
                                      padding: "2px 8px",
                                      borderRadius: "4px",
                                      marginBottom: "5px",
                                      fontWeight: "bold",
                                      fontSize: "11px",
                                      textAlign: "center",
                                    }}
                                  >
                                    📊 {agency}预报
                                  </div>
                                  <div
                                    style={{ fontSize: "12px", color: "#333" }}
                                  >
                                    <div>
                                      <strong>预报时间：</strong>
                                      {new Date(
                                        point.forecast_time
                                      ).toLocaleString("zh-CN")}
                                    </div>
                                    <div>
                                      <strong>中心位置：</strong>
                                      {point.latitude.toFixed(2)}°N,{" "}
                                      {normalizedLng.toFixed(2)}°E
                                    </div>
                                    {point.center_pressure && (
                                      <div>
                                        <strong>中心气压：</strong>
                                        {point.center_pressure} hPa
                                      </div>
                                    )}
                                    {point.max_wind_speed && (
                                      <div>
                                        <strong>最大风速：</strong>
                                        {point.max_wind_speed} m/s
                                      </div>
                                    )}
                                  </div>
                                </Tooltip>
                              </CircleMarker>
                            );
                          })}
                        </React.Fragment>
                      );
                    })}
                  </React.Fragment>
                );
              }
            )}
        </MapContainer>

        {/* 地图图层切换按钮 */}
        <div
          style={{
            position: "absolute",
            top: "10px",
            left: "10px",
            zIndex: 1000,
            display: "flex",
            flexDirection: "column",
            gap: "4px",
            background: "white",
            padding: "5px",
            borderRadius: "4px",
            boxShadow: "0 1px 4px rgba(0,0,0,0.15)",
          }}
        >
          <div style={{ display: "flex", gap: "4px" }}>
            <button
              onClick={() => setMapLayer("terrain")}
              style={{
                padding: "4px 6px",
                border:
                  mapLayer === "terrain"
                    ? "1px solid #667eea"
                    : "1px solid #ddd",
                background: mapLayer === "terrain" ? "#f0f4ff" : "white",
                color: mapLayer === "terrain" ? "#667eea" : "#333",
                borderRadius: "3px",
                cursor: "pointer",
                fontSize: "11px",
                fontWeight: mapLayer === "terrain" ? "bold" : "normal",
              }}
            >
              🗺️ 地形
            </button>
            <button
              onClick={() => setMapLayer("satellite")}
              style={{
                padding: "4px 6px",
                border:
                  mapLayer === "satellite"
                    ? "1px solid #667eea"
                    : "1px solid #ddd",
                background: mapLayer === "satellite" ? "#f0f4ff" : "white",
                color: mapLayer === "satellite" ? "#667eea" : "#333",
                borderRadius: "3px",
                cursor: "pointer",
                fontSize: "11px",
                fontWeight: mapLayer === "satellite" ? "bold" : "normal",
              }}
            >
              🛰️ 卫星
            </button>
          </div>
        </div>

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

        {/* 预测加载提示 */}
        {predictionLoading && (
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              background: "rgba(255, 255, 255, 0.95)",
              padding: "20px 30px",
              borderRadius: "12px",
              boxShadow: "0 4px 20px rgba(0,0,0,0.2)",
              zIndex: 1000,
              textAlign: "center",
            }}
          >
            <div
              style={{
                width: "40px",
                height: "40px",
                border: "4px solid #f3f3f3",
                borderTop: "4px solid #ff6b6b",
                borderRadius: "50%",
                animation: "spin 1s linear infinite",
                margin: "0 auto 10px",
              }}
            />
            <p style={{ margin: 0, color: "#333", fontWeight: "bold" }}>
              预测计算中...
            </p>
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

        {/* 鼠标位置经纬度显示 */}
        {mousePosition && (
          <div
            style={{
              position: "absolute",
              bottom: "10px",
              left: "10px",
              background: "rgba(255, 255, 255, 0.95)",
              padding: "8px 12px",
              borderRadius: "6px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
              zIndex: 1000,
              fontSize: "11px",
              fontFamily: "monospace",
              color: "#333",
            }}
          >
            <strong>Latitude:</strong> {mousePosition.lat.toFixed(6)}° |{" "}
            <strong>Longitude:</strong> {mousePosition.lng.toFixed(6)}°
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

            {/* 预测图例 */}
            {predictionData && predictionData.length > 0 && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "5px",
                  marginBottom: "12px",
                  paddingBottom: "12px",
                  borderBottom: "2px solid #ff6b6b",
                }}
              >
                <div
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "#ff6b6b",
                    marginBottom: "3px",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  <span>🤖</span>
                  <span>预测路径 (24h)</span>
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
                      background: "#ff6b6b",
                      borderRadius: "2px",
                      border: "1px dashed #ff6b6b",
                    }}
                  />
                  <span>预测轨迹</span>
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
                      width: "10px",
                      height: "10px",
                      background: "#ff6b6b",
                      borderRadius: "50%",
                      border: "2px solid white",
                      boxShadow: "0 0 4px rgba(255,107,107,0.6)",
                    }}
                  />
                  <span>预测点</span>
                </div>
              </div>
            )}

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
              {[
                { name: "热带低压 (TD)", color: "#3498db" },
                { name: "热带风暴 (TS)", color: "#2ecc71" },
                { name: "强热带风暴 (STS)", color: "#f1c40f" },
                { name: "台风 (TY)", color: "#e67e22" },
                { name: "强台风 (STY)", color: "#e74c3c" },
                { name: "超强台风 (SuperTY)", color: "#c0392b" },
              ].map((item) => (
                <div
                  key={item.name}
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
                      background: item.color,
                      borderRadius: "2px",
                    }}
                  />
                  <span>{item.name}</span>
                </div>
              ))}
            </div>

            {/* 预测路径图例 */}
            {forecastData.size > 0 && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "5px",
                  paddingTop: "8px",
                  borderTop: "1px solid #e0e0e0",
                }}
              >
                <div
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "#666",
                    marginBottom: "3px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <span>机构预测路径</span>
                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                      cursor: "pointer",
                      fontSize: "11px",
                      fontWeight: "normal",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={showForecast}
                      onChange={(e) => setShowForecast(e.target.checked)}
                      style={{ cursor: "pointer" }}
                    />
                    显示
                  </label>
                </div>
                {Array.from(forecastData.values())
                  .flat()
                  .map((agencyForecast) => (
                    <div
                      key={agencyForecast.agency}
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
                          height: "2px",
                          background: agencyForecast.color,
                          borderRadius: "1px",
                          border: `1px dashed ${agencyForecast.color}`,
                        }}
                      />
                      <span>{agencyForecast.agency}预报</span>
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 右侧预测结果面板 */}
      {showPredictionPanel && predictionData && predictionData.length > 0 && (
        <div
          style={{
            width: "350px",
            background: "#f9fafb",
            borderRadius: "10px",
            padding: "20px",
            overflowY: "auto",
            boxShadow: "-2px 0 10px rgba(0,0,0,0.1)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "15px",
            }}
          >
            <h3 style={{ margin: 0, color: "#ff6b6b" }}>🤖 预测结果</h3>
            <button
              onClick={() => setShowPredictionPanel(false)}
              style={{
                background: "none",
                border: "none",
                fontSize: "20px",
                cursor: "pointer",
                color: "#666",
              }}
            >
              ×
            </button>
          </div>

          {/* 预测概览 */}
          <div
            style={{
              background: "white",
              padding: "15px",
              borderRadius: "8px",
              marginBottom: "15px",
              border: "2px solid #ff6b6b",
            }}
          >
            <h4 style={{ margin: "0 0 10px 0", fontSize: "14px" }}>
              📊 预测概览
            </h4>
            <div style={{ fontSize: "13px", color: "#666" }}>
              <p style={{ margin: "5px 0" }}>
                <strong>台风编号：</strong>
                {selectedPoint?.typhoonId}
              </p>
              <p style={{ margin: "5px 0" }}>
                <strong>预测起点：</strong>
                {selectedPoint &&
                  new Date(
                    selectedPoint.timestamp || selectedPoint.record_time
                  ).toLocaleString("zh-CN")}
              </p>
              <p style={{ margin: "5px 0" }}>
                <strong>预测时长：</strong>24小时
              </p>
              <p style={{ margin: "5px 0" }}>
                <strong>预测点数：</strong>
                {predictionData.length}个
              </p>
            </div>
          </div>

          {/* 预测详情列表 */}
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <h4 style={{ margin: "0", fontSize: "14px" }}>📍 预测详情</h4>
            {predictionData.map((point, index) => (
              <div
                key={index}
                style={{
                  background: "white",
                  padding: "12px",
                  borderRadius: "8px",
                  borderLeft: `4px solid ${getConfidenceColor(point.confidence)}`,
                  fontSize: "12px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "8px",
                  }}
                >
                  <span style={{ fontWeight: "bold", color: "#333" }}>
                    预测点 {index + 1}
                  </span>
                  <span
                    style={{
                      color: getConfidenceColor(point.confidence),
                      fontWeight: "bold",
                    }}
                  >
                    {(point.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <p style={{ margin: "4px 0", color: "#666" }}>
                  <strong>时间：</strong>
                  {new Date(point.forecast_time).toLocaleString("zh-CN")}
                </p>
                <p style={{ margin: "4px 0", color: "#666" }}>
                  <strong>位置：</strong>
                  {point.predicted_latitude?.toFixed(2)}°N,{" "}
                  {point.predicted_longitude?.toFixed(2)}°E
                </p>
                <p style={{ margin: "4px 0", color: "#666" }}>
                  <strong>气压：</strong>
                  {point.predicted_pressure?.toFixed(0)} hPa
                </p>
                <p style={{ margin: "4px 0", color: "#666" }}>
                  <strong>风速：</strong>
                  {point.predicted_wind_speed?.toFixed(1)} m/s
                </p>
                <p style={{ margin: "4px 0", color: "#666" }}>
                  <strong>强度：</strong>
                  <span
                    style={{
                      padding: "2px 6px",
                      borderRadius: "3px",
                      background:
                        point.predicted_wind_speed >= 32
                          ? "#fee2e2"
                          : "#fef3c7",
                      color:
                        point.predicted_wind_speed >= 32
                          ? "#dc2626"
                          : "#d97706",
                      fontWeight: "bold",
                    }}
                  >
                    {getIntensityLevel(
                      point.predicted_wind_speed,
                      point.predicted_pressure
                    )}
                  </span>
                </p>
              </div>
            ))}
          </div>

          {/* 使用说明 */}
          <div
            style={{
              marginTop: "20px",
              padding: "12px",
              background: "#f0f4ff",
              borderRadius: "8px",
              fontSize: "12px",
              color: "#667eea",
            }}
          >
            <strong>💡 提示：</strong>
            点击地图上的任意路径点，即可生成从该点开始的24小时预测。
          </div>
        </div>
      )}
    </div>
  );
}

export default PredictionVisualization;
