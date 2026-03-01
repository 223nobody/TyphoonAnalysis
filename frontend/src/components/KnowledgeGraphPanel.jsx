/**
 * 知识图谱检索结果面板组件（优化版）
 * 展示检索结果的图谱可视化和上下文信息
 * 参考 KnowledgeGraphVisualization.jsx 实现
 * 全屏模式：顶部关系类型筛选 + 底部节点类型筛选
 */
import React, { useEffect, useRef, useState, useCallback } from "react";
import {
  Button,
  Spin,
  Empty,
  Tag,
  Tooltip,
  Badge,
  Card,
  Checkbox,
  Row,
  Col,
} from "antd";
import {
  CloseOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  NodeIndexOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  ReloadOutlined,
  FilterOutlined,
} from "@ant-design/icons";
import * as echarts from "echarts";
import {
  NodeType,
  NODE_TYPE_CONFIG,
  RELATIONSHIP_TYPE_CONFIG,
  ENTITY_TYPES,
  RELATIONSHIP_TYPES,
} from "../services/knowledgeGraphConfig";
import "../styles/KnowledgeGraphPanel.css";

/**
 * 知识图谱检索结果面板（GraphRAG增强版）
 */
const KnowledgeGraphPanel = ({
  isVisible,
  searchResults,
  graphContext,
  onClose,
  isLoading,
  seedEntities,
  traversalStats,
  reasoningPaths,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [hiddenEntityTypes, setHiddenEntityTypes] = useState([]);
  const [hiddenRelationshipTypes, setHiddenRelationshipTypes] = useState([]);
  const [layout, setLayout] = useState("grid");
  const chartRef = useRef(null);
  const chartInstance = useRef(null);
  const panelRef = useRef(null);
  const graphContainerRef = useRef(null);

  // 节点和关系数据
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [relationshipCounts, setRelationshipCounts] = useState({});

  // 提取节点和关系数据
  useEffect(() => {
    if (searchResults) {
      const nodes = extractNodes(searchResults);
      const links = extractLinks(searchResults);
      setGraphData({ nodes, links });
      // 计算关系类型统计
      calculateRelationshipCounts(links);
    }
  }, [searchResults]);

  // 计算关系类型数量
  const calculateRelationshipCounts = (links) => {
    const counts = {};
    links.forEach((link) => {
      counts[link.type] = (counts[link.type] || 0) + 1;
    });
    setRelationshipCounts(counts);
  };

  // 标记是否是首次展开
  const isFirstExpand = useRef(true);

  // 初始化ECharts - 只在组件挂载和展开时执行
  useEffect(() => {
    // 只有在可见、未收起、有数据时才初始化
    if (isVisible && !isCollapsed && graphData.nodes.length > 0) {
      // 使用较长的延迟确保DOM完全渲染并获取正确尺寸
      const initTimer = setTimeout(() => {
        if (!chartRef.current) return;

        // 获取容器的实际尺寸
        const containerWidth = chartRef.current.clientWidth;
        const containerHeight = chartRef.current.clientHeight;

        // 如果尺寸为0，说明DOM还未准备好，跳过初始化
        if (containerWidth === 0 || containerHeight === 0) {
          console.warn("图表容器尺寸为0，跳过初始化");
          return;
        }

        // 如果不是首次展开，先销毁旧实例确保干净状态
        if (!isFirstExpand.current && chartInstance.current) {
          chartInstance.current.dispose();
          chartInstance.current = null;
        }
        isFirstExpand.current = false;

        // 如果图表实例不存在，重新初始化
        if (!chartInstance.current) {
          chartInstance.current = echarts.init(chartRef.current);

          // 点击事件
          chartInstance.current.on("click", (params) => {
            if (params.dataType === "node") {
              setSelectedNode(params.data);
            }
          });
        }

        // 更新图表
        updateChart();

        // 强制resize
        requestAnimationFrame(() => {
          chartInstance.current?.resize();
        });
      }, 300); // 增加延迟确保DOM完全准备好

      return () => clearTimeout(initTimer);
    }

    // 当收起或不可见时，销毁图表实例
    if ((isCollapsed || !isVisible) && chartInstance.current) {
      chartInstance.current.dispose();
      chartInstance.current = null;
      isFirstExpand.current = true; // 重置标记
    }
  }, [isVisible, isCollapsed, graphData.nodes.length, layout]);

  // 当过滤条件或布局变化时，更新图表（不重新初始化）
  useEffect(() => {
    if (chartInstance.current && graphData.nodes.length > 0) {
      updateChart();
    }
  }, [
    graphData,
    hiddenEntityTypes,
    hiddenRelationshipTypes,
    layout,
    isFullscreen,
  ]);

  // 窗口大小变化时重新调整图表
  useEffect(() => {
    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // 监听全屏变化
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isFs = !!document.fullscreenElement;
      setIsFullscreen(isFs);
      setTimeout(() => {
        chartInstance.current?.resize();
      }, 100);
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () =>
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  /**
   * 切换全屏 - 只全屏图谱可视化区域
   */
  const toggleFullscreen = useCallback(() => {
    if (!graphContainerRef.current) return;

    if (!document.fullscreenElement) {
      graphContainerRef.current.requestFullscreen().catch(() => {
        // 全屏切换失败，静默处理
      });
    } else {
      document.exitFullscreen();
    }
  }, []);

  /**
   * 更新ECharts图表
   */
  const updateChart = useCallback(() => {
    if (!chartInstance.current || graphData.nodes.length === 0) return;

    // 过滤隐藏的实体类型和关系类型
    let filteredNodes = graphData.nodes;
    let filteredLinks = graphData.links;

    // 过滤节点类型
    if (hiddenEntityTypes.length > 0) {
      filteredNodes = graphData.nodes.filter(
        (node) => !hiddenEntityTypes.includes(node.type),
      );
    }

    // 过滤关系类型
    if (hiddenRelationshipTypes.length > 0) {
      filteredLinks = graphData.links.filter(
        (link) => !hiddenRelationshipTypes.includes(link.type),
      );
    }

    // 只保留与可见节点相关的关系
    const visibleNodeIds = new Set(filteredNodes.map((n) => n.id));
    filteredLinks = filteredLinks.filter(
      (link) =>
        visibleNodeIds.has(link.source) && visibleNodeIds.has(link.target),
    );

    const { nodes, links } = { nodes: filteredNodes, links: filteredLinks };
    const nodeCount = nodes.length;

    // 根据节点数量动态调整节点大小
    const baseSize = nodeCount > 50 ? 20 : nodeCount > 20 ? 25 : 35;
    const seedNodeSize = baseSize * 1.5;

    // 转换节点数据 - 为力导向布局设置初始位置
    const chartNodes = nodes.map((node, index) => {
      const config =
        NODE_TYPE_CONFIG[node.type] || NODE_TYPE_CONFIG[NodeType.TYPHOON];
      const isSeed = seedEntities?.some(
        (se) => se.entity_id === node.id || se.entity_name === node.name,
      );

      // 为节点设置初始位置（螺旋分布），减少环形感
      const goldenAngle = Math.PI * (3 - Math.sqrt(5)); // 黄金角
      const angle = index * goldenAngle;
      const radius = 30 * Math.sqrt(index + 1); // 半径随索引增加
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius;

      return {
        id: node.id,
        name: node.name || node.id,
        category: ENTITY_TYPES.findIndex((t) => t.type === node.type) || 0,
        symbolSize: isSeed ? seedNodeSize : baseSize,
        value: node.data || {},
        // 设置初始位置
        x: x,
        y: y,
        // 种子节点固定位置
        fixed: isSeed,
        itemStyle: {
          color: config.color || "#999",
          borderColor: isSeed ? "#fff" : "transparent",
          borderWidth: isSeed ? 3 : 0,
          shadowBlur: isSeed ? 15 : 0,
          shadowColor: isSeed ? config.color : "transparent",
        },
        label: {
          show: true,
          fontSize: isSeed ? 13 : 11,
          fontWeight: isSeed ? "bold" : "normal",
        },
        ...node,
      };
    });

    // 转换关系数据
    const chartLinks = links.map((link) => {
      const relConfig = RELATIONSHIP_TYPE_CONFIG[link.type] || {};
      return {
        source: link.source,
        target: link.target,
        relation: relConfig.label || link.type,
        value: link.data || {},
        lineStyle: {
          color: relConfig.color || "#999",
          width: nodeCount > 50 ? 1 : 2,
          curveness: 0.2,
        },
        ...link,
      };
    });

    // 获取布局配置
    const getLayoutConfig = () => {
      const baseConfig = {
        type: "graph",
        layout: layout,
        data: chartNodes,
        links: chartLinks,
        categories: ENTITY_TYPES.map((t) => ({
          name: t.label,
          itemStyle: { color: t.color },
        })),
        roam: true,
        draggable: true,
        label: {
          show: true,
          position: "right",
          formatter: "{b}",
          fontSize: 11,
          fontWeight: "bold",
          color: "#333",
          backgroundColor: "rgba(255,255,255,0.7)",
          padding: [2, 4],
          borderRadius: 4,
        },
        emphasis: {
          focus: "adjacency",
          lineStyle: { width: 4 },
          label: { show: true, fontSize: 14 },
        },
        lineStyle: {
          color: "source",
          curveness: 0.2,
          width: nodeCount > 50 ? 1 : 2,
          opacity: 0.7,
        },
        edgeLabel: {
          show: nodeCount <= 30,
          formatter: (params) => params?.data?.relation || "",
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
            repulsion: 1200,
            edgeLength: [120, 350],
            gravity: 0.05,
            layoutAnimation: false,
            friction: 0.9,
          },
        };
      } else if (layout === "circular") {
        return {
          ...baseConfig,
          layout: "circular",
          circular: { rotateLabel: true },
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
          lineStyle: {
            color: "source",
            curveness: 0.1,
            width: 1.5,
            opacity: 0.6,
          },
          edgeLabel: { show: false },
        };
      } else if (layout === "grid") {
        return {
          ...baseConfig,
          layout: "force",
          force: {
            repulsion: 600,
            edgeLength: [80, 200],
            gravity: 0.1,
            layoutAnimation: false,
            friction: 0.9,
          },
          symbolSize: (value, params) => {
            return params.data.category === 0 ? 45 : 22;
          },
          label: {
            show: true,
            position: "bottom",
            formatter: "{b}",
            fontSize: 11,
            fontWeight: "normal",
            color: "#333",
            distance: 5,
          },
          lineStyle: {
            color: "source",
            curveness: 0,
            width: 1.5,
            opacity: 0.6,
          },
          edgeLabel: { show: false },
          emphasis: {
            focus: "adjacency",
            lineStyle: { width: 3 },
            label: { show: true, fontSize: 13, fontWeight: "bold" },
          },
        };
      }

      return baseConfig;
    };

    const getGlobalAnimationConfig = () => {
      if (layout === "force" || layout === "grid") {
        return {
          animationDuration: 600,
          animationEasing: "cubicOut",
          animationDurationUpdate: 300,
          animationEasingUpdate: "cubicOut",
        };
      }
      return {
        animationDuration: 1000,
        animationEasing: "cubicOut",
        animationDurationUpdate: 500,
        animationEasingUpdate: "cubicOut",
      };
    };

    const option = {
      backgroundColor: isFullscreen ? "#ffffff" : "transparent",
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(255, 255, 255, 0.95)",
        borderColor: "#e0e0e0",
        borderWidth: 1,
        textStyle: { color: "#333" },
        formatter: (params) => {
          if (params.dataType === "node") {
            return formatNodeTooltip(params.data);
          } else {
            return formatEdgeTooltip(params.data);
          }
        },
      },
      ...getGlobalAnimationConfig(),
      series: [getLayoutConfig()],
    };

    chartInstance.current.setOption(option, {
      notMerge: true,
      lazyUpdate: true,
    });
  }, [
    graphData,
    seedEntities,
    hiddenEntityTypes,
    hiddenRelationshipTypes,
    layout,
    isFullscreen,
  ]);

  /**
   * 格式化节点提示框
   */
  const formatNodeTooltip = (data) => {
    const props = data.value || {};
    const type = data.type || "Unknown";
    const config = NODE_TYPE_CONFIG[type] || {};

    let html = `<div style="padding: 12px; max-width: 280px;">`;
    html += `<div style="font-weight: bold; margin-bottom: 8px; color: ${config.color || "#333"}; font-size: 14px;">${data.name}</div>`;
    html += `<div style="color: #666; font-size: 12px; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #eee;">类型: ${config.label || type}</div>`;

    if (props.year) {
      html += `<div style="font-size: 12px; margin: 4px 0;"><span style="color: #999;">年份:</span> ${props.year}</div>`;
    }
    if (props.max_wind_speed) {
      html += `<div style="font-size: 12px; margin: 4px 0;"><span style="color: #999;">最大风速:</span> ${props.max_wind_speed} m/s</div>`;
    }
    if (props.min_pressure) {
      html += `<div style="font-size: 12px; margin: 4px 0;"><span style="color: #999;">最低气压:</span> ${props.min_pressure} hPa</div>`;
    }

    html += `</div>`;
    return html;
  };

  /**
   * 格式化边提示框
   */
  const formatEdgeTooltip = (data) => {
    const relType = data.type || data.relation || "RELATED_TO";
    const config = RELATIONSHIP_TYPE_CONFIG[relType] || {};

    return `<div style="padding: 10px;">
      <div style="font-weight: bold; color: ${config.color || "#333"}; margin-bottom: 4px;">${config.label || relType}</div>
      <div style="font-size: 11px; color: #666;">${data.source} → ${data.target}</div>
    </div>`;
  };

  /**
   * 从搜索结果中提取节点
   */
  const extractNodes = (results) => {
    const nodes = [];
    if (!results) return nodes;

    if (results.nodes) {
      results.nodes.forEach((node) => {
        const nodeType = node.type || node.labels?.[0];
        let nodeName =
          node.properties?.name_cn || node.properties?.name || node.id;

        if (nodeType === "PathPoint" || nodeType === "PATH_POINT") {
          const sequence =
            node.properties?.sequence || node.id?.split("_pp_")?.[1];
          const typhoonId =
            node.properties?.typhoon_id || node.id?.split("_pp_")?.[0];
          nodeName = `路径点${sequence ? " #" + sequence : ""}`;
          node.properties = {
            ...node.properties,
            _displayName: nodeName,
            _typhoonId: typhoonId,
          };
        }

        nodes.push({
          id: node.id,
          name: nodeName,
          type: nodeType,
          data: node.properties,
        });
      });
      return nodes;
    }

    if (results.typhoons) {
      results.typhoons.forEach((typhoon) => {
        nodes.push({
          id: typhoon.typhoon_id,
          name: typhoon.name_cn || typhoon.name_en || typhoon.typhoon_id,
          type: "Typhoon",
          data: typhoon,
        });
      });
    }

    return nodes;
  };

  /**
   * 从搜索结果中提取关系
   */
  const extractLinks = (results) => {
    const links = [];
    if (!results) return links;

    const relationships = results.relationships || [];

    relationships.forEach((rel) => {
      links.push({
        source: rel.source,
        target: rel.target,
        type: rel.type,
        data: rel.properties,
      });
    });

    return links;
  };

  /**
   * 处理缩放
   */
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
      chartInstance.current.dispatchAction({ type: "restore" });
    }
  };

  /**
   * 处理关系类型点击（显示/隐藏）
   */
  const handleRelationshipTypeToggle = (relType) => {
    const isHidden = hiddenRelationshipTypes.includes(relType);
    if (isHidden) {
      setHiddenRelationshipTypes(
        hiddenRelationshipTypes.filter((t) => t !== relType),
      );
    } else {
      setHiddenRelationshipTypes([...hiddenRelationshipTypes, relType]);
    }
  };

  /**
   * 处理节点类型点击（显示/隐藏）
   */
  const handleEntityTypeToggle = (entityType) => {
    const isHidden = hiddenEntityTypes.includes(entityType);
    if (isHidden) {
      setHiddenEntityTypes(hiddenEntityTypes.filter((t) => t !== entityType));
    } else {
      setHiddenEntityTypes([...hiddenEntityTypes, entityType]);
    }
  };

  /**
   * 全选/取消全选关系类型
   */
  const handleSelectAllRelationships = () => {
    if (hiddenRelationshipTypes.length === 0) {
      // 全部隐藏
      setHiddenRelationshipTypes(RELATIONSHIP_TYPES.map((r) => r.type));
    } else {
      // 全部显示
      setHiddenRelationshipTypes([]);
    }
  };

  /**
   * 全选/取消全选节点类型
   */
  const handleSelectAllEntityTypes = () => {
    if (hiddenEntityTypes.length === 0) {
      setHiddenEntityTypes(ENTITY_TYPES.map((t) => t.type));
    } else {
      setHiddenEntityTypes([]);
    }
  };

  /**
   * 渲染顶部关系类型筛选栏（全屏模式）
   */
  const renderRelationshipFilterBar = () => {
    if (!isFullscreen) return null;

    return (
      <div className="kg-filter-bar relationship-filter-bar">
        <div className="filter-bar-header">
          <FilterOutlined />
          <span>关系类型筛选</span>
          <Button
            type="link"
            size="small"
            onClick={handleSelectAllRelationships}
          >
            {hiddenRelationshipTypes.length === 0 ? "全部隐藏" : "全部显示"}
          </Button>
        </div>
        <div className="filter-bar-content">
          <Checkbox.Group
            value={RELATIONSHIP_TYPES.filter(
              (r) => !hiddenRelationshipTypes.includes(r.type),
            ).map((r) => r.type)}
            className="relationship-checkbox-group"
          >
            <Row gutter={[8, 8]}>
              {RELATIONSHIP_TYPES.map((rel) => {
                const isHidden = hiddenRelationshipTypes.includes(rel.type);
                const count = relationshipCounts[rel.type] || 0;
                return (
                  <Col key={rel.type}>
                    <Checkbox
                      value={rel.type}
                      onChange={() => handleRelationshipTypeToggle(rel.type)}
                    >
                      <Tag
                        color={isHidden ? "#ccc" : rel.color}
                        style={{
                          marginLeft: 4,
                          opacity: isHidden ? 0.5 : 1,
                        }}
                      >
                        {rel.label}
                        {count > 0 && (
                          <span className="relation-count">({count})</span>
                        )}
                      </Tag>
                    </Checkbox>
                  </Col>
                );
              })}
            </Row>
          </Checkbox.Group>
        </div>
      </div>
    );
  };

  /**
   * 渲染底部节点类型筛选栏（全屏模式）
   */
  const renderEntityTypeFilterBar = () => {
    if (!isFullscreen) return null;

    return (
      <div className="kg-filter-bar entity-type-filter-bar">
        <div className="filter-bar-header">
          <FilterOutlined />
          <span>节点类型筛选</span>
          <Button type="link" size="small" onClick={handleSelectAllEntityTypes}>
            {hiddenEntityTypes.length === 0 ? "全部隐藏" : "全部显示"}
          </Button>
        </div>
        <div className="filter-bar-content">
          <div className="entity-type-buttons">
            {ENTITY_TYPES.map((type) => {
              const isHidden = hiddenEntityTypes.includes(type.type);
              const count = graphData.nodes.filter(
                (n) => n.type === type.type,
              ).length;
              return (
                <div
                  key={type.type}
                  className={`entity-type-button ${isHidden ? "hidden" : ""}`}
                  onClick={() => handleEntityTypeToggle(type.type)}
                >
                  <span
                    className="entity-type-dot"
                    style={{
                      backgroundColor: isHidden ? "#ccc" : type.color,
                    }}
                  />
                  <span className="entity-type-label">
                    {type.label} ({count})
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  /**
   * 渲染底部水平图例（非全屏模式）
   */
  const renderLegend = () => {
    if (isFullscreen) return null;

    return (
      <div className="kg-panel-legend-horizontal">
        {ENTITY_TYPES.map((type) => {
          const isHidden = hiddenEntityTypes.includes(type.type);
          const count = graphData.nodes.filter(
            (n) => n.type === type.type,
          ).length;
          return (
            <div
              key={type.type}
              className={`legend-item-horizontal ${isHidden ? "hidden" : ""}`}
              onClick={() => handleEntityTypeToggle(type.type)}
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
    );
  };

  /**
   * 获取质量等级对应的颜色
   */
  const getQualityColor = (level) => {
    switch (level) {
      case "high":
        return "success";
      case "medium":
        return "warning";
      case "low":
        return "default";
      default:
        return "blue";
    }
  };

  /**
   * 渲染图谱上下文
   */
  const renderContextText = () => {
    if (!graphContext && !searchResults) {
      return null;
    }

    if (graphContext?.text) {
      return (
        <Card className="context-text-card" size="small">
          <div className="context-text-header">
            <span className="context-text-title">图谱上下文</span>
            <Tag color={getQualityColor(graphContext?.quality_level)}>
              {graphContext?.quality_level === "high"
                ? "高质量"
                : graphContext?.quality_level === "medium"
                  ? "中等质量"
                  : "基础检索"}
            </Tag>
          </div>
          <pre className="context-text-content">{graphContext.text}</pre>
        </Card>
      );
    }

    const lines = [];

    if (graphContext?.query) {
      lines.push(`查询: ${graphContext.query}`);
      lines.push("");
    }

    const typhoonSeeds = seedEntities?.filter(
      (e) => e.entity_type === "Typhoon" && e.entity_name !== "台风",
    );
    if (typhoonSeeds && typhoonSeeds.length > 0) {
      lines.push(`根据知识图谱检索，找到${typhoonSeeds.length}个相关台风：`);
      typhoonSeeds.slice(0, 15).forEach((entity) => {
        const matchType =
          entity.match_type === "semantic"
            ? "[语义]"
            : entity.match_type === "hybrid"
              ? "[混合]"
              : "[关键词]";
        lines.push(`- ${entity.entity_name} ${matchType}`);
      });
      if (typhoonSeeds.length > 15) {
        lines.push(`... 还有 ${typhoonSeeds.length - 15} 个台风`);
      }
      lines.push("");
    }

    if (traversalStats) {
      lines.push(
        `检索统计：知识图谱中包含 ${traversalStats.node_count || 0} 个相关实体，${traversalStats.relationship_count || 0} 个关系。`,
      );
    }

    if (reasoningPaths && reasoningPaths.length > 0) {
      lines.push("");
      lines.push("推理路径：");
      reasoningPaths.forEach((path, index) => {
        lines.push(`${index + 1}. ${path.path_description}`);
      });
    }

    const contextText = lines.join("\n");

    return (
      <Card className="context-text-card" size="small">
        <div className="context-text-header">
          <span className="context-text-title">图谱上下文</span>
          <Tag color={getQualityColor(graphContext?.quality_level)}>
            {graphContext?.quality_level === "high"
              ? "高质量"
              : graphContext?.quality_level === "medium"
                ? "中等质量"
                : "基础检索"}
          </Tag>
        </div>
        <pre className="context-text-content">{contextText}</pre>
      </Card>
    );
  };

  if (!isVisible) return null;

  if (isCollapsed) {
    return (
      <div className="knowledge-graph-panel collapsed">
        <div
          className="panel-expand-trigger"
          onClick={() => setIsCollapsed(false)}
        >
          <MenuUnfoldOutlined />
          <span className="expand-text">GraphRAG</span>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={panelRef}
      className={`knowledge-graph-panel ${isFullscreen ? "fullscreen" : ""}`}
    >
      {/* 面板头部 */}
      <div className="panel-header">
        <div className="panel-header-left">
          <Tooltip title="收起面板">
            <Button
              type="text"
              icon={<MenuFoldOutlined />}
              onClick={() => setIsCollapsed(true)}
              className="collapse-button"
            />
          </Tooltip>
          <h3>
            <NodeIndexOutlined style={{ marginRight: 8 }} />
            GraphRAG 检索结果
          </h3>
        </div>

        <div className="panel-header-right">
          {traversalStats && (
            <Tag color="blue" className="stats-tag">
              {traversalStats.node_count || 0}节点 /
              {traversalStats.relationship_count || 0}关系
            </Tag>
          )}
          <Button
            type="text"
            icon={<CloseOutlined />}
            onClick={onClose}
            className="close-button"
          />
        </div>
      </div>

      {/* 主内容区域 */}
      <div className="panel-main-content">
        {isLoading ? (
          <div className="loading-container">
            <Spin size="large" />
            <p>正在加载图谱...</p>
          </div>
        ) : graphData.nodes.length === 0 ? (
          <Empty description="暂无图谱数据" />
        ) : (
          <>
            {/* 图谱可视化卡片 */}
            <Card className="graph-card" bodyStyle={{ padding: 0 }}>
              <div ref={graphContainerRef} className="graph-container">
                {/* 顶部关系类型筛选栏（全屏模式） */}
                {renderRelationshipFilterBar()}

                {/* 布局切换按钮（全屏模式） */}
                {isFullscreen && (
                  <div className="layout-switcher">
                    <Button
                      type={layout === "force" ? "primary" : "default"}
                      size="small"
                      onClick={() => setLayout("force")}
                    >
                      力导向
                    </Button>
                    <Button
                      type={layout === "circular" ? "primary" : "default"}
                      size="small"
                      onClick={() => setLayout("circular")}
                    >
                      环形
                    </Button>
                    <Button
                      type={layout === "grid" ? "primary" : "default"}
                      size="small"
                      onClick={() => setLayout("grid")}
                    >
                      网格
                    </Button>
                  </div>
                )}

                {/* 工具栏 */}
                <div className="graph-toolbar">
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
                <div ref={chartRef} className="graph-chart" />

                {/* 选中节点信息 */}
                {selectedNode && (
                  <div className="selected-node-info">
                    <h4>{selectedNode.name}</h4>
                    <p>类型: {selectedNode.type}</p>
                  </div>
                )}

                {/* 底部节点类型筛选栏（全屏模式） */}
                {renderEntityTypeFilterBar()}
              </div>

              {/* 底部水平图例（非全屏模式） */}
              {renderLegend()}
            </Card>

            {/* 图谱上下文 */}
            {renderContextText()}
          </>
        )}
      </div>
    </div>
  );
};

export default KnowledgeGraphPanel;
