/**
 * 知识图谱可视化界面（整合版）
 * 上下布局：上部筛选控制面板 + 下部可视化画布
 * 将 KnowledgeGraphFilter 和 KnowledgeGraphCanvas 整合到本组件中
 * 严格按照知识图谱开发文档定义节点类型和关系类型
 */
import React, { useState, useEffect, useRef } from "react";
import {
  Card,
  Typography,
  message,
  Input,
  Button,
  Select,
  Checkbox,
  Row,
  Col,
  Space,
  Tag,
  Slider,
  Tooltip,
  Spin,
  Empty,
  Badge,
} from "antd";
import {
  GlobalOutlined,
  SearchOutlined,
  ReloadOutlined,
  SettingOutlined,
  FilterOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
} from "@ant-design/icons";
import * as echarts from "echarts";
import { searchTyphoonsKG, getTyphoonRelationships } from "../services/api";
import {
  NodeType,
  NODE_TYPE_CONFIG,
  RELATIONSHIP_TYPE_CONFIG,
  ENTITY_TYPES,
  formatNodeTooltip,
  formatEdgeTooltip,
} from "../services/knowledgeGraphConfig";
import "../styles/KnowledgeGraphVisualization.css";

const { Title } = Typography;
const { Option } = Select;

// 关系类型配置
const RELATIONSHIP_TYPES = [
  // 基础关系
  { type: "HAS_PATH_POINT", label: "拥有路径点", color: "#ff6b6b" },
  { type: "NEXT", label: "路径顺序", color: "#4ecdc4" },
  { type: "OCCURRED_IN", label: "发生时间", color: "#45b7d1" },
  { type: "LANDED_AT", label: "登陆地点", color: "#96ceb4" },
  // 扩展关系 - 台风生命周期
  { type: "GENERATED_AT", label: "生成于", color: "#74b9ff" },
  { type: "DISSIPATED_AT", label: "消散于", color: "#a29bfe" },
  // 扩展关系 - 强度变化（INTENSIFIED_TO 和 WEAKENED_TO 已包含达到强度的语义）
  { type: "INTENSIFIED_TO", label: "增强为", color: "#fd79a8" },
  { type: "WEAKENED_TO", label: "减弱为", color: "#fdcb6e" },
  // 扩展关系 - 相似性
  { type: "SIMILAR_TO", label: "相似于", color: "#6c5ce7" },
  // 扩展关系 - 地理影响（AFFECTED_AREA 包含经过附近的语义）
  { type: "AFFECTED_AREA", label: "影响区域", color: "#e17055" },
];

// 布局选项
const LAYOUT_OPTIONS = [
  { value: "force", label: "力导向布局" },
  { value: "circular", label: "环形布局" },
  { value: "grid", label: "网格布局" },
];

const KnowledgeGraphVisualization = () => {
  // ===== 核心状态 =====
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [relationshipCounts, setRelationshipCounts] = useState({});
  const [currentTyphoonId, setCurrentTyphoonId] = useState(null); // 当前显示的台风ID

  // ===== 可视化设置状态（修改后实时同步到图表）=====
  const [selectedRelationships, setSelectedRelationships] = useState(
    RELATIONSHIP_TYPES.map((r) => r.type),
  );
  const [layout, setLayout] = useState("force");
  const [nodeLimit, setNodeLimit] = useState(1000);

  // ===== 搜索状态 =====
  const [searchQuery, setSearchQuery] = useState("");
  const [searchDepth, setSearchDepth] = useState(2);

  // ===== 原始 KnowledgeGraphCanvas 的状态 =====
  const chartRef = useRef(null);
  const chartInstance = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [hiddenEntityTypes, setHiddenEntityTypes] = useState([]);

  // ===== 初始化 =====
  useEffect(() => {
    loadDefaultData();
  }, []);

  // ===== 图表初始化 =====
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
      setTimeout(() => {
        chartInstance.current?.resize();
      }, 100);
    };

    const handleResize = () => {
      chartInstance.current?.resize();
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    window.addEventListener("resize", handleResize);

    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      window.removeEventListener("resize", handleResize);
      if (chartInstance.current) {
        chartInstance.current.dispose();
        chartInstance.current = null;
      }
    };
  }, []);

  // ===== 图表数据更新 =====
  // 当任何可视化设置变化时，实时更新图表
  useEffect(() => {
    if (!graphData?.nodes || graphData.nodes.length === 0) {
      return;
    }

    if (!chartRef.current) {
      return;
    }

    if (!chartInstance.current) {
      console.log("初始化图表");
      chartInstance.current = echarts.init(chartRef.current);

      chartInstance.current.on("click", (params) => {
        if (params.dataType === "node") {
          setSelectedNode(params.data.id);
          handleNodeClick(params.data);
        }
      });

      chartInstance.current.on("dblclick", (params) => {
        if (params.dataType === "node") {
          handleNodeDoubleClick(params.data);
        }
      });
    }

    console.log("数据更新触发:", {
      hasChart: !!chartInstance.current,
      nodesCount: graphData?.nodes?.length,
      loading,
      layout,
      selectedRelationshipsCount: selectedRelationships.length,
      nodeLimit,
    });

    updateChart();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphData, layout, selectedRelationships, nodeLimit, hiddenEntityTypes]);

  // ===== 数据转换函数 =====
  const transformNodeData = (nodes) => {
    return nodes.map((node) => {
      const label = node.labels?.[0] || "Unknown";
      const config = NODE_TYPE_CONFIG[label] || NODE_TYPE_CONFIG["Typhoon"];
      return {
        ...node,
        category: label,
        name: node.properties?.name_cn || node.properties?.name || node.id,
        symbolSize: config.symbolSize,
        itemStyle: {
          color: config.color,
        },
      };
    });
  };

  const transformLinkData = (links) => {
    return links.map((link) => {
      const relType =
        typeof link.type === "string"
          ? link.type
          : link.type?.value || link.type;
      const relConfig = RELATIONSHIP_TYPE_CONFIG[relType] || {};
      return {
        ...link,
        type: relType,
        relation: relConfig.label || relType,
        // 不在这里设置 lineStyle，在 updateChart 中统一设置
        // 这样可以确保 curveness 等属性正确应用
      };
    });
  };

  // ===== 数据加载函数 =====
  const loadDefaultData = async () => {
    setLoading(true);
    try {
      const defaultTyphoonId = "202602";
      const data = await getTyphoonRelationships(defaultTyphoonId, searchDepth);
      console.log("API返回数据:", data);
      if (data?.nodes && data?.links) {
        const transformedNodes = transformNodeData(data.nodes);
        const transformedLinks = transformLinkData(data.links);
        console.log("转换后节点:", transformedNodes);
        console.log("转换后关系:", transformedLinks);
        setGraphData({
          nodes: transformedNodes,
          links: transformedLinks,
        });
        setCurrentTyphoonId(defaultTyphoonId);
        calculateRelationshipCounts(transformedLinks);
      }
    } catch (error) {
      console.error("加载知识图谱数据失败:", error);
      message.error("加载知识图谱数据失败");
    } finally {
      setLoading(false);
    }
  };

  const calculateRelationshipCounts = (links) => {
    const counts = {};
    links.forEach((link) => {
      counts[link.type] = (counts[link.type] || 0) + 1;
    });
    setRelationshipCounts(counts);
  };

  // ===== 加载指定台风数据（支持搜索深度实时更新）=====
  const loadTyphoonData = async (typhoonId) => {
    if (!typhoonId) return;

    setLoading(true);
    try {
      const data = await getTyphoonRelationships(typhoonId, searchDepth);
      console.log("关系网络数据:", data);

      if (data?.nodes && data?.links) {
        const transformedNodes = transformNodeData(data.nodes);
        const transformedLinks = transformLinkData(data.links);
        console.log("转换后节点:", transformedNodes);
        console.log("转换后关系:", transformedLinks);
        setGraphData({
          nodes: transformedNodes,
          links: transformedLinks,
        });
        setCurrentTyphoonId(typhoonId);
        calculateRelationshipCounts(transformedLinks);
        message.success(`已加载台风数据 (深度: ${searchDepth})`);
      } else {
        message.warning(`台风 ${typhoonId} 没有关系数据`);
      }
    } catch (error) {
      console.error("加载台风数据失败:", error);
      message.error("加载台风数据失败");
    } finally {
      setLoading(false);
    }
  };

  // ===== 搜索深度变化时自动重新加载数据 =====
  useEffect(() => {
    if (currentTyphoonId) {
      console.log(
        `搜索深度变化为 ${searchDepth}，重新加载台风 ${currentTyphoonId}`,
      );
      loadTyphoonData(currentTyphoonId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchDepth]);

  // ===== 图表更新函数 =====
  const updateChart = () => {
    if (!chartInstance.current) return;

    // 构建过滤配置，直接使用当前状态
    const filterConfig = {
      relationshipTypes: selectedRelationships,
      layout,
      nodeLimit,
    };

    console.log("updateChart - 原始数据:", graphData);
    console.log("updateChart - 过滤配置:", filterConfig);

    let filteredData = filterGraphData(graphData, filterConfig);
    console.log("updateChart - 过滤后数据:", filteredData);

    if (hiddenEntityTypes.length > 0) {
      const visibleNodes = filteredData.nodes.filter(
        (node) => !hiddenEntityTypes.includes(node.category),
      );
      const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));
      filteredData = {
        nodes: visibleNodes,
        links: filteredData.links.filter(
          (link) =>
            visibleNodeIds.has(link.source) && visibleNodeIds.has(link.target),
        ),
      };
      console.log("updateChart - 隐藏类型后数据:", filteredData);
    }

    if (filteredData.nodes.length === 0) {
      console.log("updateChart - 没有节点，清空图表");
      chartInstance.current.clear();
      return;
    }

    const typhoonNodes = filteredData.nodes.filter(
      (n) => n.category === NodeType.TYPHOON,
    );
    let centerNodeId = null;
    if (typhoonNodes.length > 0) {
      centerNodeId = typhoonNodes[0].id;
    }

    const chartData = filteredData.nodes.map((node) => {
      const config =
        NODE_TYPE_CONFIG[node.category] || NODE_TYPE_CONFIG[NodeType.TYPHOON];
      return {
        id: node.id,
        name: node.name || node.id,
        category: ENTITY_TYPES.findIndex((t) => t.type === node.category) || 0,
        symbolSize: config.symbolSize,
        value: node.properties || {},
        fixed:
          layout === "circular" && node.id === centerNodeId ? true : undefined,
        x: layout === "circular" && node.id === centerNodeId ? 0 : undefined,
        y: layout === "circular" && node.id === centerNodeId ? 0 : undefined,
        ...node,
      };
    });

    // 处理关系数据，支持同一对节点之间的多条关系显示
    // 使用 Map 来统计同一 source-target-type 对的关系数量
    // 注意：即使 source-target 相同，不同类型（增强/减弱）的关系也应该分开显示
    const linkGroups = new Map();
    filteredData.links.forEach((link, index) => {
      // 分组键包含 source、target 和 type，确保不同类型关系分开显示
      const key = `${link.source}-${link.target}-${link.type}`;
      if (!linkGroups.has(key)) {
        linkGroups.set(key, []);
      }
      linkGroups.get(key).push({ ...link, originalIndex: index });
    });

    // 调试：检查是否有同一 source-target 但不同类型（INTENSIFIED_TO vs WEAKENED_TO）的关系
    const debugSourceTarget = new Map();
    filteredData.links.forEach((link) => {
      const key = `${link.source}-${link.target}`;
      if (!debugSourceTarget.has(key)) {
        debugSourceTarget.set(key, []);
      }
      debugSourceTarget.get(key).push(link.type);
    });
    const multiTypePairs = Array.from(debugSourceTarget.entries()).filter(
      ([key, types]) => new Set(types).size > 1,
    );
    if (multiTypePairs.length > 0) {
      console.log("同一 source-target 对但有不同类型的关系:", multiTypePairs);
    }

    const chartLinks = filteredData.links.map((link, index) => {
      const relConfig = RELATIONSHIP_TYPE_CONFIG[link.type] || {};
      // 使用包含 type 的键来获取分组
      const key = `${link.source}-${link.target}-${link.type}`;
      const group = linkGroups.get(key);
      const groupIndex = group.findIndex((l) => l.originalIndex === index);
      const totalInGroup = group.length;

      // 计算曲率：同一对节点之间的多条关系使用不同的曲率，使其分开显示
      // 基础曲率 0.2，每条额外的关系增加 0.15 的曲率，正负交替
      let curveness = 0.2;
      if (totalInGroup > 1) {
        // 多条关系时，使用不同的曲率值
        const offset = Math.ceil(groupIndex / 2) * 0.2;
        curveness = groupIndex % 2 === 0 ? 0.2 + offset : -(0.2 + offset);
      }

      return {
        ...link,
        source: link.source,
        target: link.target,
        relation: relConfig.label || link.type,
        value: link.properties || {},
        // 添加唯一 ID，避免 ECharts 合并
        id: `${link.source}-${link.target}-${link.type}-${index}`,
        // 设置曲率，使多条关系分开显示
        // 注意：lineStyle 放在最后，确保覆盖 link 中可能存在的 lineStyle
        lineStyle: {
          color: relConfig.color || "#999",
          curveness: curveness,
        },
      };
    });

    // 调试：检查最终生成的 chartLinks
    console.log("生成的 chartLinks 数量:", chartLinks.length);
    console.log(
      "前5条关系:",
      chartLinks.slice(0, 5).map((l) => ({
        source: l.source,
        target: l.target,
        type: l.type,
        curveness: l.lineStyle?.curveness,
      })),
    );

    const getLayoutConfig = () => {
      const baseConfig = {
        type: "graph",
        layout: layout,
        data: chartData,
        links: chartLinks,
        categories: ENTITY_TYPES.map((t) => ({
          name: t.label,
          itemStyle: { color: t.color },
        })),
        roam: true,
        label: {
          show: true,
          position: "right",
          formatter: "{b}",
          fontSize: 12,
          fontWeight: "bold",
        },
        emphasis: {
          focus: "adjacency",
          lineStyle: {
            width: 4,
          },
        },
        // 注意：不在 baseConfig 中设置 lineStyle，让每条关系使用自己的 lineStyle
        // lineStyle 已在 chartLinks 中为每条关系单独设置
        edgeLabel: {
          show: true,
          formatter: (params) => {
            try {
              const relation = params?.data?.relation || params?.relation || "";
              const properties =
                params?.data?.value || params?.data?.properties || {};
              // 如果有时间信息，显示在标签中
              if (properties && properties.change_time) {
                const timeStr = properties.change_time.substring(0, 10); // 只显示日期部分
                return `${relation}\n${timeStr}`;
              }
              return relation;
            } catch (e) {
              return "";
            }
          },
          fontSize: 9,
          color: "#666",
        },
        edgeSymbol: ["circle", "arrow"],
        edgeSymbolSize: [4, 10],
      };

      if (layout === "force") {
        return {
          ...baseConfig,
          force: {
            repulsion: 1000,
            edgeLength: [100, 300],
            gravity: 0.1,
            layoutAnimation: true,
          },
        };
      } else if (layout === "circular") {
        return {
          ...baseConfig,
          layout: "circular",
          circular: {
            rotateLabel: true,
          },
          symbolSize: (value, params) => {
            return params.data.category === 0 ? 60 : 25;
          },
          label: {
            show: true,
            position: "outside",
            formatter: "{b}",
            fontSize: 11,
            fontWeight: "normal",
            color: "#333",
          },
          // 不在 circular 布局中设置 lineStyle，使用每条关系自己的 lineStyle
          edgeLabel: {
            show: false,
          },
        };
      } else if (layout === "grid") {
        return {
          ...baseConfig,
          layout: "force",
          force: {
            repulsion: 800,
            edgeLength: [80, 200],
            gravity: 0.2,
            layoutAnimation: true,
          },
          symbolSize: (value, params) => {
            return params.data.category === 0 ? 50 : 20;
          },
          label: {
            show: true,
            position: "bottom",
            formatter: "{b}",
            fontSize: 10,
            fontWeight: "normal",
            color: "#333",
          },
          // 不在 grid 布局中设置 lineStyle，使用每条关系自己的 lineStyle
          edgeLabel: {
            show: false,
          },
        };
      }

      return baseConfig;
    };

    const option = {
      backgroundColor: isFullscreen ? "#ffffff" : "#fafafa",
      tooltip: {
        trigger: "item",
        formatter: (params) => {
          try {
            if (params.dataType === "node") {
              return formatNodeTooltip(params.data);
            } else {
              return formatEdgeTooltip(params.data);
            }
          } catch (error) {
            return "数据加载中...";
          }
        },
      },
      animationDuration: 1500,
      animationEasingUpdate: "quinticInOut",
      series: [getLayoutConfig()],
    };

    chartInstance.current.setOption(option, {
      notMerge: true,
      lazyUpdate: false,
    });

    setTimeout(() => {
      chartInstance.current?.resize();
    }, 100);
  };

  const filterGraphData = (data, filters) => {
    if (!data?.nodes || !data?.links) {
      return { nodes: [], links: [] };
    }

    let resultNodes = [...data.nodes];
    let resultLinks = [...data.links];

    // 应用关系类型过滤
    if (filters.relationshipTypes && filters.relationshipTypes.length > 0) {
      const actualRelationshipTypes = new Set(
        data.links.map((link) => link.type),
      );

      const matchedTypes = filters.relationshipTypes.filter((type) =>
        actualRelationshipTypes.has(type),
      );

      if (matchedTypes.length > 0) {
        resultLinks = data.links.filter((link) =>
          matchedTypes.includes(link.type),
        );

        const relatedNodeIds = new Set();
        resultLinks.forEach((link) => {
          relatedNodeIds.add(link.source);
          relatedNodeIds.add(link.target);
        });

        // 始终保留台风节点
        const typhoonNodes = data.nodes.filter(
          (n) => n.category === NodeType.TYPHOON,
        );
        typhoonNodes.forEach((n) => relatedNodeIds.add(n.id));

        resultNodes = data.nodes.filter((node) => relatedNodeIds.has(node.id));
      }
    }

    // 应用节点数量限制
    if (
      filters.nodeLimit &&
      filters.nodeLimit > 0 &&
      resultNodes.length > filters.nodeLimit
    ) {
      // 优先保留台风节点，然后按类型排序保留其他节点
      const typhoonNodes = resultNodes.filter(
        (n) => n.category === NodeType.TYPHOON,
      );
      const otherNodes = resultNodes.filter(
        (n) => n.category !== NodeType.TYPHOON,
      );

      const remainingSlots = Math.max(
        0,
        filters.nodeLimit - typhoonNodes.length,
      );
      const limitedOtherNodes = otherNodes.slice(0, remainingSlots);

      resultNodes = [...typhoonNodes, ...limitedOtherNodes];

      // 只保留与剩余节点相关的关系
      const remainingNodeIds = new Set(resultNodes.map((n) => n.id));
      resultLinks = resultLinks.filter(
        (link) =>
          remainingNodeIds.has(link.source) &&
          remainingNodeIds.has(link.target),
      );
    }

    return {
      nodes: resultNodes,
      links: resultLinks,
    };
  };

  // ===== 事件处理函数 =====
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    try {
      const searchResults = await searchTyphoonsKG({
        query: searchQuery.trim(),
        query_type: "fuzzy",
        limit: 1,
      });

      console.log("搜索结果:", searchResults);

      if (searchResults?.length > 0) {
        const typhoonId = searchResults[0].typhoon_id;
        await loadTyphoonData(typhoonId);
      } else {
        message.warning("未找到匹配的台风");
      }
    } catch (error) {
      console.error("搜索失败:", error);
      message.error("搜索失败");
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    loadDefaultData();
  };

  const handleResetLayout = () => {
    setLayout("force");
    message.success("布局已重置");
  };

  const handleNodeClick = (nodeData) => {
    console.log("节点点击:", nodeData);
  };

  const handleNodeDoubleClick = (nodeData) => {
    console.log("节点双击:", nodeData);
  };

  const handleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  };

  const handleEntityTypeToggle = (entityType, isHidden) => {
    console.log(`实体类型 ${entityType} ${isHidden ? "隐藏" : "显示"}`);
  };

  // ===== Filter 组件的事件处理 =====
  const handleRelationshipChange = (checkedValues) => {
    setSelectedRelationships(checkedValues);
  };

  const handleSelectAll = () => {
    if (selectedRelationships.length === RELATIONSHIP_TYPES.length) {
      setSelectedRelationships([]);
    } else {
      setSelectedRelationships(RELATIONSHIP_TYPES.map((r) => r.type));
    }
  };

  // ===== Canvas 组件的事件处理 =====
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      chartRef.current?.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  };

  const handleZoomIn = () => {
    if (chartInstance.current) {
      const option = chartInstance.current.getOption();
      const currentZoom = option.series[0].zoom || 1;
      chartInstance.current.setOption({
        series: [{ zoom: currentZoom * 1.2 }],
      });
    }
  };

  const handleZoomOut = () => {
    if (chartInstance.current) {
      const option = chartInstance.current.getOption();
      const currentZoom = option.series[0].zoom || 1;
      chartInstance.current.setOption({
        series: [{ zoom: currentZoom / 1.2 }],
      });
    }
  };

  const handleReset = () => {
    if (chartInstance.current) {
      chartInstance.current.dispatchAction({
        type: "restore",
      });
    }
  };

  const handleLegendClick = (type) => {
    const isHidden = hiddenEntityTypes.includes(type.type);
    const newHiddenTypes = isHidden
      ? hiddenEntityTypes.filter((t) => t !== type.type)
      : [...hiddenEntityTypes, type.type];
    setHiddenEntityTypes(newHiddenTypes);
    handleEntityTypeToggle(type.type, !isHidden);
  };

  return (
    <div className="knowledge-graph-visualization">
      {/* ===== 筛选控制面板 ===== */}
      <Card
        className="kg-filter-card"
        title={
          <Space>
            <FilterOutlined />
            <span>台风知识图谱可视化</span>
          </Space>
        }
        extra={
          <Space>
            <Tooltip title="Neo4j Browser">
              <Button
                icon={<GlobalOutlined />}
                onClick={() =>
                  window.open("http://localhost:7474/browser/", "_blank")
                }
                size="small"
              >
                Neo4j Browser
              </Button>
            </Tooltip>
            <Tooltip title={isFullscreen ? "退出全屏" : "全屏显示"}>
              <Button
                icon={
                  isFullscreen ? (
                    <FullscreenExitOutlined />
                  ) : (
                    <FullscreenOutlined />
                  )
                }
                onClick={handleFullscreen}
                size="small"
              >
                {isFullscreen ? "退出全屏" : "全屏"}
              </Button>
            </Tooltip>
            <Tooltip title="刷新数据">
              <Button
                icon={<ReloadOutlined />}
                onClick={handleRefresh}
                loading={loading}
                size="small"
              >
                刷新
              </Button>
            </Tooltip>
            <Tooltip title="重置布局">
              <Button
                icon={<SettingOutlined />}
                onClick={handleResetLayout}
                size="small"
              >
                重置布局
              </Button>
            </Tooltip>
          </Space>
        }
      >
        {/* 关系类型过滤区 */}
        <div className="filter-section">
          <div className="filter-section-title">
            <span>关系类型过滤</span>
            <Button type="link" size="small" onClick={handleSelectAll}>
              {selectedRelationships.length === RELATIONSHIP_TYPES.length
                ? "取消全选"
                : "全选"}
            </Button>
          </div>
          <Checkbox.Group
            value={selectedRelationships}
            onChange={handleRelationshipChange}
            className="relationship-checkbox-group"
          >
            <Row gutter={[8, 8]}>
              {RELATIONSHIP_TYPES.map((rel) => (
                <Col key={rel.type}>
                  <Checkbox value={rel.type}>
                    <Tag color={rel.color} style={{ marginLeft: 4 }}>
                      {rel.label}
                      {relationshipCounts[rel.type] !== undefined && (
                        <span className="relation-count">
                          ({relationshipCounts[rel.type]})
                        </span>
                      )}
                    </Tag>
                  </Checkbox>
                </Col>
              ))}
            </Row>
          </Checkbox.Group>
        </div>

        {/* 布局设置区 */}
        <div className="filter-section">
          <div className="filter-section-title">布局设置</div>
          <Row gutter={16} align="middle">
            <Col span={8}>
              <Select
                value={layout}
                onChange={setLayout}
                style={{ width: "100%" }}
                placeholder="选择布局"
              >
                {LAYOUT_OPTIONS.map((opt) => (
                  <Option key={opt.value} value={opt.value}>
                    {opt.label}
                  </Option>
                ))}
              </Select>
            </Col>
            <Col span={16}>
              <div className="slider-container">
                <span className="slider-label">节点数量限制:</span>
                <Slider
                  min={100}
                  max={2000}
                  step={100}
                  value={nodeLimit}
                  onChange={setNodeLimit}
                  style={{ flex: 1, marginLeft: 8 }}
                />
                <span className="slider-value">{nodeLimit}</span>
              </div>
            </Col>
          </Row>
        </div>

        {/* 节点搜索区 */}
        <div className="filter-section">
          <div className="filter-section-title">节点搜索</div>
          <Row gutter={16} align="middle">
            <Col flex="auto">
              <Input.Search
                placeholder="输入节点名称搜索...(支持台风中文名或编号 2601或202601)"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onSearch={handleSearch}
                enterButton={<SearchOutlined />}
                loading={loading}
              />
            </Col>
            <Col>
              <div className="search-depth-container">
                <span className="depth-label">搜索深度:</span>
                <Select
                  value={searchDepth}
                  onChange={setSearchDepth}
                  style={{ width: 80 }}
                >
                  <Option value={1}>1级</Option>
                  <Option value={2}>2级</Option>
                  <Option value={3}>3级</Option>
                </Select>
              </div>
            </Col>
          </Row>
        </div>
      </Card>

      {/* ===== 可视化画布 ===== */}
      <Card className="kg-canvas-card">
        <div
          className={`kg-canvas-container ${isFullscreen ? "fullscreen" : ""}`}
        >
          {/* 工具栏 */}
          <div className="kg-canvas-toolbar">
            <Tooltip title="放大">
              <Button
                icon={<ZoomInOutlined />}
                onClick={handleZoomIn}
                size="small"
              />
            </Tooltip>
            <Tooltip title="缩小">
              <Button
                icon={<ZoomOutOutlined />}
                onClick={handleZoomOut}
                size="small"
              />
            </Tooltip>
            <Tooltip title="重置视图">
              <Button
                icon={<ReloadOutlined />}
                onClick={handleReset}
                size="small"
              />
            </Tooltip>
            <Tooltip title={isFullscreen ? "退出全屏" : "全屏显示"}>
              <Button
                icon={
                  isFullscreen ? (
                    <FullscreenExitOutlined />
                  ) : (
                    <FullscreenOutlined />
                  )
                }
                onClick={toggleFullscreen}
                size="small"
              />
            </Tooltip>
          </div>

          {/* 图表区域 */}
          <div
            ref={chartRef}
            className="kg-canvas-chart"
            style={{ position: "relative" }}
          >
            {loading && (
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: "rgba(255,255,255,0.7)",
                  zIndex: 10,
                }}
              >
                <Spin size="large" tip="加载知识图谱..." />
              </div>
            )}
            {!loading &&
              (!graphData?.nodes || graphData.nodes.length === 0) && (
                <div
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Empty
                    description={
                      <span>
                        暂无数据
                        <br />
                        <small>请使用上方筛选条件加载图谱</small>
                      </span>
                    }
                  />
                </div>
              )}
          </div>

          {/* 底部图例 */}
          <div className="kg-canvas-legend-horizontal">
            {ENTITY_TYPES.map((type) => {
              const isHidden = hiddenEntityTypes.includes(type.type);
              const count = graphData.nodes.filter(
                (n) => n.category === type.type,
              ).length;
              return (
                <div
                  key={type.type}
                  className={`legend-item-horizontal ${isHidden ? "hidden" : ""}`}
                  onClick={() => handleLegendClick(type)}
                >
                  <span
                    className="legend-dot"
                    style={{
                      backgroundColor: isHidden ? "#ccc" : type.color,
                      opacity: isHidden ? 0.5 : 1,
                    }}
                  />
                  <span
                    className="legend-label"
                    style={{ opacity: isHidden ? 0.5 : 1 }}
                  >
                    {type.label} ({count})
                  </span>
                </div>
              );
            })}
            <div className="legend-stats">
              <Badge
                count={graphData.nodes.length}
                style={{ backgroundColor: "#1890ff" }}
              />
              <span className="stats-label">节点</span>
              <Badge
                count={graphData.links.length}
                style={{ backgroundColor: "#52c41a", marginLeft: 8 }}
              />
              <span className="stats-label">关系</span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default KnowledgeGraphVisualization;
