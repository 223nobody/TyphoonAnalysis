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
 *
 * @param {number} lng - 原始经度值
 * @returns {number} 归一化后的经度值（-180 到 180 之间）
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

// 创建警戒线文字标注图标 - 竖排显示
const createWarningLineLabel = (text, color) => {
  // 将文字拆分成单个字符，竖排显示
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

  // 遍历360度，计算每个角度的半径
  for (let i = 0; i <= numPoints; i++) {
    const angle = (i * 360) / numPoints;

    const radian = (angle * Math.PI) / 180;

    let radiusMultiplier;
    if (angle > 90 && angle < 180) {
      // 西北象限（地图左上角）：半径放大
      radiusMultiplier = northwestRadiusMultiplier;
    } else {
      // 其他方向：保持原始半径
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

// 地图控制器组件 - 用于处理地图定位、缩放监听和鼠标位置追踪
function MapController({ center, zoom, onZoomChange, onMouseMove }) {
  const map = useMap();

  useEffect(() => {
    if (center && center.length === 2 && zoom) {
      console.log(
        `🗺️ 地图定位到: [${center[0]}, ${center[1]}], 缩放级别: ${zoom}`,
      );
      map.setView(center, zoom, {
        animate: true,
        duration: 1.0,
      });
    }
  }, [center, zoom, map]);

  // 监听地图缩放变化
  useEffect(() => {
    const handleZoomEnd = () => {
      const currentZoom = map.getZoom();
      console.log(`🔍 地图缩放级别变化: ${currentZoom}`);
      if (onZoomChange) {
        onZoomChange(currentZoom);
      }
    };

    // 监听缩放结束事件
    map.on("zoomend", handleZoomEnd);

    // 初始化时也触发一次，获取当前缩放级别
    const initialZoom = map.getZoom();
    console.log(`🔍 地图初始缩放级别: ${initialZoom}`);
    if (onZoomChange) {
      onZoomChange(initialZoom);
    }

    return () => {
      map.off("zoomend", handleZoomEnd);
    };
  }, [map, onZoomChange]);

  // 监听鼠标移动事件
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

function MapVisualization({
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

  // 筛选条件
  const [filters, setFilters] = useState({
    year: "2026", // 默认2026年
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
  const [mapLayer, setMapLayer] = useState("terrain"); // "terrain" 或 "satellite"

  // 地图中心和缩放状态
  const [mapCenter, setMapCenter] = useState([23.5, 120.0]); // 默认中心位置
  const [mapZoom, setMapZoom] = useState(3); // 默认缩放级别（调整为原来的一半）

  // 跟踪上一次选中的台风集合，用于检测新选中的台风
  const [prevSelectedTyphoons, setPrevSelectedTyphoons] = useState(new Set());

  // 跟踪最近一次被可视化的台风ID
  const [latestVisualizedTyphoon, setLatestVisualizedTyphoon] = useState(null);

  // 视频播放相关状态
  const [videoModalVisible, setVideoModalVisible] = useState(false);
  const [videoUrl, setVideoUrl] = useState("");
  const [videoLoading, setVideoLoading] = useState(false);
  const [videoError, setVideoError] = useState(null);
  const [currentTyphoonId, setCurrentTyphoonId] = useState(null);
  const videoRef = useRef(null);

  // 鼠标位置经纬度状态
  const [mousePosition, setMousePosition] = useState(null);

  // 收藏相关状态
  const [collectTyphoons, setCollectTyphoons] = useState([]);
  const [isCollecting, setIsCollecting] = useState(false);

  // 使用ref跟踪是否已经处理过URL参数，避免重复处理
  const hasProcessedUrlTyphoonId = useRef(false);
  const hasTriedYearSwitch = useRef(false);

  // 处理URL参数中的typhoon_id - 第一阶段：提取年份并切换
  useEffect(() => {
    if (urlTyphoonId && !hasProcessedUrlTyphoonId.current) {
      console.log(`📌 检测到URL参数中的typhoon_id: ${urlTyphoonId}`);

      // 验证typhoon_id格式
      if (!urlTyphoonId || urlTyphoonId.trim() === "") {
        message.error("台风ID格式错误");
        hasProcessedUrlTyphoonId.current = true;
        return;
      }

      // 从typhoon_id中提取年份（假设格式为YYNNNN，如2501表示2025年01号台风）
      const typhoonIdStr = String(urlTyphoonId);
      let targetYear = null;

      if (typhoonIdStr.length >= 2) {
        const yearPrefix = typhoonIdStr.substring(0, 2);
        targetYear = parseInt("20" + yearPrefix);

        if (!isNaN(targetYear) && targetYear >= 2000 && targetYear <= 2099) {
          console.log(`📅 从typhoon_id提取年份: ${targetYear}`);

          // 如果当前年份与目标年份不同，切换年份
          if (filters.year !== targetYear.toString()) {
            console.log(`🔄 切换年份从 ${filters.year} 到 ${targetYear}`);
            setFilters((prev) => ({ ...prev, year: targetYear.toString() }));
            hasTriedYearSwitch.current = true;
          }
        }
      }
    }
  }, [urlTyphoonId, filters.year]);

  // 处理URL参数中的typhoon_id - 第二阶段：在数据加载完成后选中台风
  useEffect(() => {
    // 只在以下条件下执行：
    // 1. 有URL参数
    // 2. 没有处理过
    // 3. 数据加载完成（listLoading为false）
    // 4. 台风列表有数据
    if (
      urlTyphoonId &&
      !hasProcessedUrlTyphoonId.current &&
      !listLoading &&
      typhoons.length > 0
    ) {
      const typhoonExists = typhoons.some((t) => t.typhoon_id === urlTyphoonId);

      if (typhoonExists) {
        // 台风存在，自动选中
        console.log(`✅ 台风 ${urlTyphoonId} 存在于列表中，自动选中`);
        if (onTyphoonSelect) {
          // 检查是否已经选中了这个台风
          if (!selectedTyphoons.has(urlTyphoonId)) {
            console.log(`🎯 调用 onTyphoonSelect 选中台风 ${urlTyphoonId}`);
            onTyphoonSelect(urlTyphoonId);
          } else {
            console.log(`ℹ️ 台风 ${urlTyphoonId} 已经被选中，跳过`);
          }
          // 无论是否调用onTyphoonSelect，都标记为已处理
          hasProcessedUrlTyphoonId.current = true;
        }
      } else {
        // 台风不在列表中
        if (hasTriedYearSwitch.current) {
          // 如果已经尝试过切换年份但还是找不到，显示警告
          console.warn(
            `⚠️ 台风 ${urlTyphoonId} 在列表中未找到（已尝试切换年份）`,
          );
          message.warning(`台风 ${urlTyphoonId} 在当前年份列表中未找到`);
          hasProcessedUrlTyphoonId.current = true;
        } else {
          // 如果还没尝试过切换年份，说明还在默认年份，等待年份切换完成
          console.log(`⏳ 等待年份切换完成以查找台风 ${urlTyphoonId}`);
        }
      }
    }
  }, [
    urlTyphoonId,
    typhoons,
    listLoading,
    onTyphoonSelect,
    selectedTyphoons,
    filters.year,
  ]);

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
  }, [filters.year, filters.status]); // 当年份或状态筛选条件变化时重新加载

  // 应用前端搜索筛选（仅用于名称搜索）
  useEffect(() => {
    applyFilters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typhoons, filters.search]); // 当台风数据或搜索关键词变化时重新筛选

  // 当选中的台风变化时，加载路径数据并定位地图
  useEffect(() => {
    console.log(`🔄 selectedTyphoons 变化:`, Array.from(selectedTyphoons));

    if (selectedTyphoons && selectedTyphoons.size > 0) {
      console.log(`📥 开始加载台风路径数据...`);
      loadTyphoonPaths();

      // 检测新选中的台风并定位地图
      const newlySelected = Array.from(selectedTyphoons).find(
        (id) => !prevSelectedTyphoons.has(id),
      );

      if (newlySelected) {
        console.log(`🆕 新选中的台风: ${newlySelected}`);
        // 找到新选中的台风数据
        const typhoon = typhoons.find((t) => t.typhoon_id === newlySelected);
        if (typhoon) {
          centerMapOnTyphoon(newlySelected);
        }
        // 更新最近一次被可视化的台风ID
        setLatestVisualizedTyphoon(newlySelected);
      }

      // 更新上一次选中的台风集合
      setPrevSelectedTyphoons(new Set(selectedTyphoons));
    } else {
      console.log(`🗑️ 清空所有路径数据`);
      // 当没有选中任何台风时，清空所有路径数据
      setPathsData(new Map());
      setForecastData(new Map()); // 同时清空预测路径数据
      setPrevSelectedTyphoons(new Set());
      setLatestVisualizedTyphoon(null); // 清空最近可视化的台风ID
    }
  }, [selectedTyphoons, typhoons]);

  // 加载台风列表 - 修复：传递年份参数到后端API
  const loadTyphoons = async () => {
    try {
      setListLoading(true);
      setListError(null);

      console.log(`📡 开始加载台风列表，年份: ${filters.year}`);

      // 构建查询参数
      const params = {
        limit: 100,
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
        console.log(`✅ 台风列表加载成功，数量: ${data.items.length}`);
        setTyphoons(data.items);
      } else if (data && Array.isArray(data)) {
        console.log(`✅ 台风列表加载成功，数量: ${data.length}`);
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
      console.error("收藏操作失败:", err);
      message.error(err.message || "操作失败");
    } finally {
      setIsCollecting(false);
    }
  };

  // 应用前端筛选
  const applyFilters = () => {
    let filtered = [...typhoons];

    console.log(`🔄 应用筛选，原始台风数量: ${filtered.length}`);

    // 搜索筛选（在前端处理，因为需要模糊匹配）
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(
        (t) =>
          t.typhoon_id.toLowerCase().includes(searchLower) ||
          t.typhoon_name.toLowerCase().includes(searchLower) ||
          (t.typhoon_name_cn && t.typhoon_name_cn.includes(filters.search)),
      );
    }

    console.log(`✅ 筛选后台风数量: ${filtered.length}`);
    console.log(
      `📋 筛选后的台风列表:`,
      filtered.map((t) => t.typhoon_id),
    );
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

      loadForecastPaths();
    } catch (err) {
      console.error("加载台风预测路径失败:", err);
      setPathError(err.message || "加载失败，请稍后重试");
    } finally {
      setPathLoading(false);
    }
  };

  // 加载预测路径数据 - 只对活跃台风请求
  const loadForecastPaths = async () => {
    try {
      setForecastLoading(true);
      const newForecastData = new Map();

      for (const typhoonId of selectedTyphoons) {
        try {
          // 查找台风信息，检查是否为活跃台风
          const typhoonInfo = typhoons.find((t) => t.typhoon_id === typhoonId);

          // 只对活跃台风（status=1）请求预报数据
          if (!typhoonInfo || typhoonInfo.status !== 1) {
            console.log(
              `台风 ${typhoonId} 不是活跃台风（status=${typhoonInfo?.status}），跳过预报数据请求`,
            );
            continue;
          }

          const data = await getTyphoonForecast(typhoonId);
          if (data && Array.isArray(data) && data.length > 0) {
            newForecastData.set(typhoonId, data);
            console.log(`台风 ${typhoonId} 预测路径数据加载成功:`, data);
            const agencies = data.map((d) => d.agency);
            console.log(`台风 ${typhoonId} 的预报机构:`, agencies);
          } else {
            console.log(`台风 ${typhoonId} 暂无预测路径数据`);
          }
        } catch (err) {
          console.error(`加载台风 ${typhoonId} 预测路径失败:`, err);
        }
      }

      setForecastData(newForecastData);
      console.log(
        `✅ 预测路径数据已更新，当前包含 ${newForecastData.size} 个台风的预测数据`,
      );
    } catch (err) {
      console.error("加载预测路径失败:", err);
    } finally {
      setForecastLoading(false);
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
    console.log(`多台风叠加显示切换: ${allowMultipleTyphoons} -> ${newValue}`);

    // 当从 true 切换到 false 时，清空所有选中的台风
    if (allowMultipleTyphoons && !newValue && selectedTyphoons.size > 0) {
      console.log("关闭多台风叠加显示，清空所有选中的台风");
      clearAllSelectedTyphoons();
    }

    setAllowMultipleTyphoons(newValue);
  };

  // 将地图中心定位到指定台风
  const centerMapOnTyphoon = async (typhoonId) => {
    try {
      // 获取台风路径数据
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
          const lng = parseFloat(latestPoint.longitude); // 直接使用原始经度

          console.log(
            `✅ 地图定位到台风 ${typhoonId} 的中心位置: [${lat}, ${lng}]`,
          );

          // 更新地图中心和缩放级别
          setMapCenter([lat, lng]);
          setMapZoom(5);
        } else {
          console.warn(`⚠️ 台风 ${typhoonId} 的路径点缺少经纬度信息`);
        }
      } else {
        console.warn(`⚠️ 台风 ${typhoonId} 暂无路径数据`);
      }
    } catch (error) {
      console.error(`❌ 定位台风 ${typhoonId} 失败:`, error);
    }
  };

  // 获取年份列表（从当前年份到2000年）
  const getYears = () => {
    const currentYear = new Date().getFullYear();
    const years = [];
    for (let year = currentYear; year >= 2000; year--) {
      years.push(year);
    }
    return years;
  };

  // 根据强度获取颜色（优化配色方案）
  const getColorByIntensity = (intensity) => {
    const colorMap = {
      热带低压: "#3498db", // 蓝色
      热带风暴: "#2ecc71", // 绿色
      强热带风暴: "#f1c40f", // 黄色
      台风: "#e67e22", // 橙色
      强台风: "#e74c3c", // 红色
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

    // 归一化经度值用于显示
    const normalizedLng = normalizeLongitudeForDisplay(point.longitude);

    // 判断是东经还是西经
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
      </div>
    );
  };

  // 🎬 视频播放处理函数 - 直接拼接OSS视频URL
  const handlePlayVideo = async (typhoonId) => {
    try {
      setVideoLoading(true);
      setVideoError(null);
      setCurrentTyphoonId(typhoonId);

      // 将台风ID转换为6位格式（年份2位 + 编号4位）
      const formatTyphoonId = (id) => {
        const idStr = String(id);
        // 如果已经是6位，直接返回
        if (idStr.length === 6) {
          return idStr;
        }
        // 如果是4位（如2501），前面补20（表示20xx年）
        if (idStr.length === 4) {
          return "20" + idStr;
        }
      };

      // 拼接视频URL
      const formattedId = formatTyphoonId(typhoonId);
      const videoUrl = `https://typhoonanalysis.oss-cn-wuhan-lr.aliyuncs.com/typhoons/${formattedId}.mp4`;

      setVideoUrl(videoUrl);
      setVideoModalVisible(true);
      setVideoLoading(false);
    } catch (error) {
      console.error("加载视频失败:", error);
      setVideoError(error.message || "加载视频失败，请稍后重试");
      setVideoLoading(false);
    }
  };

  // 关闭视频模态窗口
  const handleCloseVideo = () => {
    setVideoModalVisible(false);
    setVideoUrl("");
    setVideoError(null);
    setCurrentTyphoonId(null);

    // 停止视频播放
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
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
            <p
              style={{
                margin: "5px 0 0 24px",
                fontSize: "12px",
                color: "#6b7280",
                display: "flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              {allowMultipleTyphoons ? (
                <>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                  <span>可同时显示多个台风路径</span>
                </>
              ) : (
                <>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#ef4444"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                  <span>选择新台风时清除之前的路径</span>
                </>
              )}
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
              {filteredTyphoons.map((typhoon) => {
                const isCollected = collectTyphoons.includes(
                  typhoon.typhoon_id,
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
                    onMouseEnter={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.background = "#f3f4f6";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.background = "white";
                      }
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
                        transition: "all 0.2s ease",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = "scale(1.1)";
                        if (isCollected) {
                          e.currentTarget.style.filter =
                            "drop-shadow(0 0 4px rgba(217, 119, 6, 0.4)";
                        } else {
                          e.currentTarget.style.filter =
                            "drop-shadow(0 0 4px rgba(209, 213, 219, 0.4)";
                        }
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = "scale(1)";
                        e.currentTarget.style.filter = "none";
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
          center={[30, 100]} // 调整中心点以更好地显示北半球（北纬30度，东经100度）
          zoom={1.5} // 降低缩放级别为1.5（原来的一半），显示更大区域
          minZoom={1} // 允许更小的缩放级别，可以看到更大范围
          maxZoom={18}
          style={{ width: "100%", height: "100%", zIndex: 1 }}
          ref={mapRef}
        >
          {/* 地图控制器 - 用于动态定位、缩放监听和鼠标位置追踪 */}
          <MapController
            center={mapCenter}
            zoom={mapZoom}
            onZoomChange={setMapZoom}
            onMouseMove={setMousePosition}
          />

          {/* 根据选择显示不同的地图图层 */}
          {mapLayer === "terrain" ? (
            <>
              {/* 高德地图全球版地形图 */}
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
              {/* 天地图卫星影像底图 */}
              <TileLayer
                key="tianditu-satellite"
                attribution='&copy; <a href="http://www.tianditu.gov.cn/">天地图</a>'
                url="http://t{s}.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=eb771030fd9565381964c832ef07698a"
                subdomains={["0", "1", "2", "3", "4", "5", "6", "7"]}
                maxZoom={18}
                minZoom={2}
              />
              {/* 天地图卫星影像标注图层 - 中文地名 */}
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

          {/* 2. 蓝色虚线 - 48小时警戒线（7次定位界线） */}
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

          {/* 48小时警戒线标注 - 使用Marker显示，始终显示以便调试 */}
          <Marker
            position={[28, 132]}
            icon={createWarningLineLabel("48小时警戒线", "#0000FF")}
          />

          {/* 3. 黄色虚线 - 24小时警戒线 */}
          <Polyline
            positions={[
              // 东海段
              [0, 105],
              [4.5, 113],
              // 台湾海峡段
              [4.5, 113],
              [11, 119],
              // 南海北部粤闽段
              [11, 119],
              [18, 119],
              // 南海北部琼桂段
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

          {/* 24小时警戒线标注 - 使用Marker显示，始终显示以便调试 */}
          <Marker
            position={[28, 127]}
            icon={createWarningLineLabel("24小时警戒线", "#FFB85C")}
          />

          {/* 渲染台风路径 */}
          {Array.from(pathsData.entries()).map(([typhoonId, pathPoints]) => {
            if (!pathPoints || pathPoints.length === 0) return null;

            // 获取路径坐标 - 直接使用原始经度值
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
                      >
                        <Tooltip
                          direction="top"
                          offset={[0, -10]}
                          opacity={0.95}
                        >
                          {createPopupContent(point)}
                        </Tooltip>
                      </CircleMarker>

                      {/* 台风风圈可视化效果 - 非对称风圈 */}
                      {isLatestPoint && (
                        <>
                          {/* 外层影响范围 - 7级风圈（不规则扇形） */}
                          <Polygon
                            positions={generateIrregularWindCircle(
                              [point.latitude, point.longitude],
                              120,
                              7,
                            )}
                            pathOptions={{
                              fillColor: "rgba(200, 200, 200, 0.45)",
                              color: "#aaa",
                              weight: 2,
                              fillOpacity: 0.45,
                            }}
                          />

                          {/* 中层风圈 - 10级风圈（不规则扇形） */}
                          <Polygon
                            positions={generateIrregularWindCircle(
                              [point.latitude, point.longitude],
                              65,
                              10,
                            )}
                            pathOptions={{
                              fillColor: "rgba(255, 165, 0, 0.35)",
                              color: "rgba(255, 165, 0, 0.6)",
                              weight: 2,
                              fillOpacity: 0.35,
                            }}
                          />

                          {/* 内层强风圈 - 12级风圈（不规则扇形） */}
                          <Polygon
                            positions={generateIrregularWindCircle(
                              [point.latitude, point.longitude],
                              30,
                              12,
                            )}
                            pathOptions={{
                              fillColor: "rgba(255, 255, 0, 0.4)",
                              color: "rgba(255, 255, 0, 0.7)",
                              weight: 2.5,
                              fillOpacity: 0.4,
                            }}
                          />

                          {/* 台风眼中心点 - 使用台风图标，显示完整路径点信息 */}
                          <Marker
                            position={[point.latitude, point.longitude]}
                            icon={createTyphoonIcon()}
                          >
                            <Tooltip
                              direction="top"
                              offset={[0, -30]}
                              opacity={0.95}
                              permanent={false}
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

          {/* 渲染预测路径（按预报机构分组显示） */}
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

                      // 🔗 将历史路径的最后一个点添加到预测路径的开头
                      const historicalPath = pathsData.get(typhoonId);
                      let fullForecastPath = [...points];
                      if (historicalPath && historicalPath.length > 0) {
                        const lastHistoricalPoint =
                          historicalPath[historicalPath.length - 1];
                        fullForecastPath.unshift(lastHistoricalPoint);
                      }

                      // 获取预测路径坐标 - 直接使用原始经度值
                      const forecastCoordinates = fullForecastPath.map(
                        (point) => [point.latitude, point.longitude],
                      );

                      return (
                        <React.Fragment key={`forecast-${typhoonId}-${agency}`}>
                          {/* 渲染预测路径（虚线） */}
                          <Polyline
                            positions={forecastCoordinates}
                            color={color}
                            weight={2}
                            opacity={0.7}
                            dashArray="5, 10"
                          />

                          {/* 预测路径点 */}
                          {points.map((point, index) => {
                            // 归一化经度用于显示（仅用于Tooltip显示）
                            const normalizedLng = normalizeLongitudeForDisplay(
                              point.longitude,
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
                                        point.forecast_time,
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
                                    {point.intensity && (
                                      <div>
                                        <strong>强度：</strong>
                                        {point.intensity}
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
              },
            )}
        </MapContainer>

        {/* 地图图层切换按钮 - 缩小版 */}
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
          {/* 图层切换按钮组 - 并排排列 */}
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
                transition: "all 0.2s",
                whiteSpace: "nowrap",
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
                transition: "all 0.2s",
                whiteSpace: "nowrap",
              }}
            >
              🛰️ 卫星
            </button>
          </div>

          {/* 缩放按钮组 */}
          <div style={{ display: "flex", gap: "4px" }}>
            <button
              onClick={() => {
                if (mapRef.current) {
                  mapRef.current.setZoom(mapRef.current.getZoom() + 1);
                }
              }}
              style={{
                flex: 1,
                padding: "4px 6px",
                border: "1px solid #ddd",
                background: "white",
                color: "#333",
                borderRadius: "3px",
                cursor: "pointer",
                fontSize: "14px",
                fontWeight: "bold",
                transition: "all 0.2s",
              }}
              title="放大"
            >
              +
            </button>
            <button
              onClick={() => {
                if (mapRef.current) {
                  mapRef.current.setZoom(mapRef.current.getZoom() - 1);
                }
              }}
              style={{
                flex: 1,
                padding: "4px 6px",
                border: "1px solid #ddd",
                background: "white",
                color: "#333",
                borderRadius: "3px",
                cursor: "pointer",
                fontSize: "14px",
                fontWeight: "bold",
                transition: "all 0.2s",
              }}
              title="缩小"
            >
              −
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

        {/* 鼠标位置经纬度显示 - 左下角，单行显示 */}
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
              whiteSpace: "nowrap",
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
                    <span>预测路径</span>
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
                        ></div>
                        <span>{agencyForecast.agency}预报</span>
                      </div>
                    ))}
                </div>
              )}
              {selectedTyphoons &&
                selectedTyphoons.size > 0 &&
                latestVisualizedTyphoon && (
                  <div
                    style={{
                      paddingTop: "12px",
                      borderTop: "1px solid #e0e0e0",
                    }}
                  >
                    <button
                      onClick={() => {
                        // 播放最近一次被可视化的台风视频
                        handlePlayVideo(latestVisualizedTyphoon);
                      }}
                      disabled={videoLoading}
                      style={{
                        width: "100%",
                        padding: "10px 15px",
                        background: videoLoading
                          ? "#ccc"
                          : "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                        color: "white",
                        border: "none",
                        borderRadius: "8px",
                        fontSize: "13px",
                        fontWeight: 600,
                        cursor: videoLoading ? "not-allowed" : "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "8px",
                        transition: "all 0.3s ease",
                        boxShadow: videoLoading
                          ? "none"
                          : "0 4px 15px rgba(102, 126, 234, 0.4)",
                      }}
                      onMouseEnter={(e) => {
                        if (!videoLoading) {
                          e.target.style.transform = "translateY(-2px)";
                          e.target.style.boxShadow =
                            "0 6px 20px rgba(102, 126, 234, 0.6)";
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!videoLoading) {
                          e.target.style.transform = "translateY(0)";
                          e.target.style.boxShadow =
                            "0 4px 15px rgba(102, 126, 234, 0.4)";
                        }
                      }}
                    >
                      <span style={{ fontSize: "16px" }}>
                        {videoLoading ? "⏳" : "▶️"}
                      </span>
                      <span>
                        {videoLoading ? "加载中..." : "路径动态可视化"}
                      </span>
                    </button>

                    {/* 视频错误提示 */}
                    {videoError && (
                      <div
                        style={{
                          marginTop: "8px",
                          padding: "8px",
                          background: "#fff3cd",
                          border: "1px solid #ffc107",
                          borderRadius: "6px",
                          fontSize: "12px",
                          color: "#856404",
                          textAlign: "center",
                        }}
                      >
                        ⚠️ {videoError}
                      </div>
                    )}
                  </div>
                )}
            </div>
          </div>
        )}

        {/* 🎬 视频播放模态窗口 */}
        {videoModalVisible && (
          <div
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: "rgba(0, 0, 0, 0.85)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 10000,
            }}
            onClick={handleCloseVideo}
          >
            <div
              style={{
                position: "relative",
                width: "48vw",
                height: "48vh",
                maxWidth: "960px",
                maxHeight: "540px",
                background: "#000",
                borderRadius: "12px",
                overflow: "hidden",
                boxShadow: "0 10px 40px rgba(0, 0, 0, 0.6)",
              }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* 关闭按钮 */}
              <button
                onClick={handleCloseVideo}
                style={{
                  position: "absolute",
                  top: "10px",
                  right: "10px",
                  width: "36px",
                  height: "36px",
                  background: "rgba(255, 255, 255, 0.2)",
                  border: "2px solid white",
                  borderRadius: "50%",
                  color: "white",
                  fontSize: "18px",
                  fontWeight: "bold",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  zIndex: 10001,
                  transition: "all 0.3s ease",
                }}
                onMouseEnter={(e) => {
                  e.target.style.background = "rgba(255, 255, 255, 0.3)";
                  e.target.style.transform = "scale(1.1)";
                }}
                onMouseLeave={(e) => {
                  e.target.style.background = "rgba(255, 255, 255, 0.2)";
                  e.target.style.transform = "scale(1)";
                }}
              >
                ✕
              </button>

              <video
                ref={videoRef}
                controls
                autoPlay
                preload="auto"
                width="100%"
                height="100%"
                onLoadStart={() => {
                  console.log("🎬 视频开始加载...");
                  console.log("📍 视频URL:", videoUrl);
                }}
                onLoadedMetadata={() => {
                  console.log("✅ 视频元数据加载完成");
                }}
                onCanPlay={() => {
                  console.log("✅ 视频可以播放");
                  setVideoError(null);
                }}
                onError={(e) => {
                  const video = e.target;

                  // 检查是否是source标签的错误
                  if (e.target.tagName === "SOURCE") {
                    console.error("❌ Source标签加载失败");
                    setVideoError("视频资源加载失败，请检查后端服务是否正常");
                    return;
                  }

                  // 获取错误代码
                  let errorCode = "未知";
                  let errorDetail = null;

                  if (video.error) {
                    errorCode = video.error.code;
                    errorDetail = video.error.message || null;
                  }

                  // 错误代码映射
                  const errorMessages = {
                    1: "视频加载被中止",
                    2: "网络错误导致视频下载失败",
                    3: "视频解码失败（可能是格式不支持）",
                    4: "视频资源不可用或格式不支持",
                  };

                  const errorMsg = errorMessages[errorCode] || "视频加载失败";

                  // 提供更友好的错误提示
                  let userMessage = errorMsg;
                  if (errorCode === 2) {
                    userMessage += "。请检查网络连接或后端服务是否正常。";
                  } else if (errorCode === 3 || errorCode === 4) {
                    userMessage +=
                      "。视频格式可能不被浏览器支持，建议使用Chrome或Edge浏览器。";
                  } else if (errorCode === "未知") {
                    userMessage =
                      "视频加载失败，请检查后端代理服务是否正常运行。";
                  }

                  setVideoError(userMessage);
                }}
                style={{
                  width: "100%",
                  height: "100%",
                  display: "block",
                  objectFit: "contain",
                  backgroundColor: "#000",
                }}
              >
                <source
                  src={videoUrl}
                  type="video/mp4"
                  onError={() => {
                    setVideoError("视频资源加载失败，请稍后重试");
                  }}
                />
                您的浏览器不支持视频播放
              </video>

              {/* 视频标题 */}
              <div
                style={{
                  position: "absolute",
                  bottom: 0,
                  left: 0,
                  right: 0,
                  background:
                    "linear-gradient(to top, rgba(0,0,0,0.8), transparent)",
                  padding: "15px 15px 10px",
                  color: "white",
                  fontSize: "13px",
                  fontWeight: 600,
                }}
              >
                台风 {currentTyphoonId} 路径动态可视化
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default MapVisualization;
