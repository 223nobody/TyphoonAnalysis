/**
 * 知识图谱配置模块
 * 严格按照知识图谱开发文档定义节点类型、关系类型及其属性
 *
 * 节点类型 (5种):
 * - Typhoon: 台风节点
 * - PathPoint: 路径点节点
 * - Location: 地理位置节点
 * - Time: 时间节点
 * - Intensity: 强度等级节点
 *
 * 关系类型 (11种):
 * 基础关系 (4个):
 * - HAS_PATH_POINT: 台风-路径点关系
 * - NEXT: 路径点顺序关系
 * - OCCURRED_IN: 台风-时间关系
 * - LANDED_AT: 台风-地点关系
 *
 * 扩展关系 - 台风生命周期 (2个):
 * - GENERATED_AT: 生成位置
 * - DISSIPATED_AT: 消散位置
 *
 * 扩展关系 - 强度变化 (2个):
 * - INTENSIFIED_TO: 强度增强（包含达到强度的语义）
 * - WEAKENED_TO: 强度减弱（包含达到强度的语义）
 *
 * 扩展关系 - 相似性 (1个):
 * - SIMILAR_TO: 相似台风
 *
 * 扩展关系 - 地理影响 (2个):
 * - AFFECTED_AREA: 影响区域（包含经过附近的语义）
 */

export const NodeType = {
  TYPHOON: 'Typhoon',
  PATH_POINT: 'PathPoint',
  LOCATION: 'Location',
  TIME: 'Time',
  INTENSITY: 'Intensity',
};

export const RelationshipType = {
  // 基础关系
  HAS_PATH_POINT: 'HAS_PATH_POINT',
  NEXT: 'NEXT',
  OCCURRED_IN: 'OCCURRED_IN',
  LANDED_AT: 'LANDED_AT',
  // 扩展关系 - 台风生命周期
  GENERATED_AT: 'GENERATED_AT',
  DISSIPATED_AT: 'DISSIPATED_AT',
  // 扩展关系 - 强度变化（INTENSIFIED_TO 和 WEAKENED_TO 已包含达到强度的语义）
  INTENSIFIED_TO: 'INTENSIFIED_TO',
  WEAKENED_TO: 'WEAKENED_TO',
  // 扩展关系 - 相似性
  SIMILAR_TO: 'SIMILAR_TO',
  // 扩展关系 - 地理影响（AFFECTED_AREA 包含经过附近的语义）
  AFFECTED_AREA: 'AFFECTED_AREA',
};

export const IntensityLevel = {
  TD: 'TD',
  TS: 'TS',
  STS: 'STS',
  TY: 'TY',
  STY: 'STY',
  SUPER_TY: 'SuperTY',
};

export const INTENSITY_LEVELS = {
  [IntensityLevel.TD]: { name_cn: '热带低压', wind_speed_min: 10.8, wind_speed_max: 17.1 },
  [IntensityLevel.TS]: { name_cn: '热带风暴', wind_speed_min: 17.2, wind_speed_max: 24.4 },
  [IntensityLevel.STS]: { name_cn: '强热带风暴', wind_speed_min: 24.5, wind_speed_max: 32.6 },
  [IntensityLevel.TY]: { name_cn: '台风', wind_speed_min: 32.7, wind_speed_max: 41.4 },
  [IntensityLevel.STY]: { name_cn: '强台风', wind_speed_min: 41.5, wind_speed_max: 50.9 },
  [IntensityLevel.SUPER_TY]: { name_cn: '超强台风', wind_speed_min: 51.0, wind_speed_max: 999.0 },
};

export const NODE_TYPE_CONFIG = {
  [NodeType.TYPHOON]: {
    type: NodeType.TYPHOON,
    label: '台风',
    color: '#ff6b6b',
    symbolSize: 60,
    idField: 'typhoon_id',
    displayField: 'name_cn',
    description: '台风实体节点，包含台风基本信息',
    fields: [
      { key: 'typhoon_id', label: '台风编号', type: 'string' },
      { key: 'name_cn', label: '中文名称', type: 'string' },
      { key: 'name_en', label: '英文名称', type: 'string' },
      { key: 'year', label: '年份', type: 'number' },
      { key: 'max_wind_speed', label: '最大风速(m/s)', type: 'number' },
      { key: 'min_pressure', label: '最低气压(hPa)', type: 'number' },
      { key: 'max_power', label: '最高风力等级', type: 'number' },
      { key: 'peak_intensity', label: '峰值强度等级', type: 'string' },
      { key: 'total_path_points', label: '路径点总数', type: 'number' },
      { key: 'duration_hours', label: '持续时长(小时)', type: 'number' },
      { key: 'start_lat', label: '起始纬度', type: 'number' },
      { key: 'start_lon', label: '起始经度', type: 'number' },
      { key: 'end_lat', label: '结束纬度', type: 'number' },
      { key: 'end_lon', label: '结束经度', type: 'number' },
      { key: 'avg_moving_speed', label: '平均移动速度(km/h)', type: 'number' },
      { key: 'max_moving_speed', label: '最大移动速度(km/h)', type: 'number' },
      { key: 'total_distance_km', label: '总移动距离(km)', type: 'number' },
      { key: 'landfall_count', label: '登陆次数', type: 'number' },
      { key: 'start_time', label: '生成时间', type: 'datetime' },
      { key: 'end_time', label: '消散时间', type: 'datetime' },
    ],
  },
  [NodeType.PATH_POINT]: {
    type: NodeType.PATH_POINT,
    label: '路径点',
    color: '#4ecdc4',
    symbolSize: 30,
    idField: 'typhoon_id',
    displayField: 'sequence',
    description: '台风路径点节点，记录位置和时间信息',
    fields: [
      { key: 'typhoon_id', label: '台风编号', type: 'string' },
      { key: 'sequence', label: '序列号', type: 'number' },
      { key: 'lat', label: '纬度', type: 'number' },
      { key: 'lon', label: '经度', type: 'number' },
      { key: 'timestamp', label: '时间戳', type: 'datetime' },
      { key: 'hour_of_year', label: '年内小时数', type: 'number' },
      { key: 'pressure', label: '中心气压(hPa)', type: 'number' },
      { key: 'wind_speed', label: '最大风速(m/s)', type: 'number' },
      { key: 'intensity', label: '强度等级', type: 'string' },
      { key: 'intensity_level', label: '强度代码', type: 'string' },
      { key: 'power', label: '风力等级', type: 'number' },
      { key: 'moving_direction', label: '移动方向', type: 'string' },
      { key: 'moving_speed', label: '移动速度(km/h)', type: 'number' },
      { key: 'distance_from_genesis', label: '距生成点距离(km)', type: 'number' },
      { key: 'distance_to_next', label: '到下一点距离(km)', type: 'number' },
      { key: 'pressure_trend', label: '气压变化趋势', type: 'number' },
    ],
  },
  [NodeType.LOCATION]: {
    type: NodeType.LOCATION,
    label: '地理位置',
    color: '#45b7d1',
    symbolSize: 45,
    idField: 'name',
    displayField: 'name',
    description: '地理位置节点，表示登陆地点',
    fields: [
      { key: 'name', label: '地点名称', type: 'string' },
      { key: 'lat', label: '纬度', type: 'number' },
      { key: 'lon', label: '经度', type: 'number' },
      { key: 'intensity', label: '登陆时强度', type: 'string' },
      { key: 'description', label: '描述信息', type: 'string' },
      { key: 'type', label: '类型', type: 'string' },
    ],
  },
  [NodeType.TIME]: {
    type: NodeType.TIME,
    label: '时间',
    color: '#96ceb4',
    symbolSize: 40,
    idField: 'year',
    displayField: 'year',
    description: '时间节点，表示台风发生年份',
    fields: [
      { key: 'year', label: '年份', type: 'number' },
      { key: 'total_typhoons', label: '该年台风总数', type: 'number' },
      { key: 'total_landfalls', label: '该年登陆次数', type: 'number' },
      { key: 'strongest_typhoon_id', label: '最强台风编号', type: 'string' },
      { key: 'strongest_wind_speed', label: '最强台风风速(m/s)', type: 'number' },
      { key: 'strongest_intensity_level', label: '最强台风等级', type: 'string' },
      { key: 'is_peak_season', label: '是否高发期', type: 'boolean' },
    ],
  },
  [NodeType.INTENSITY]: {
    type: NodeType.INTENSITY,
    label: '强度等级',
    color: '#ffeaa7',
    symbolSize: 45,
    idField: 'level',
    displayField: 'name_cn',
    description: '强度等级节点，表示台风强度分类（静态定义）',
    fields: [
      { key: 'level', label: '等级代码', type: 'string' },
      { key: 'name_cn', label: '中文名称', type: 'string' },
      { key: 'wind_speed_min', label: '最小风速(m/s)', type: 'number' },
      { key: 'wind_speed_max', label: '最大风速(m/s)', type: 'number' },
      // 注意：时间信息在 INTENSIFIED_TO 和 WEAKENED_TO 关系上
    ],
  },
};

export const RELATIONSHIP_TYPE_CONFIG = {
  // 基础关系
  [RelationshipType.HAS_PATH_POINT]: {
    type: RelationshipType.HAS_PATH_POINT,
    label: '拥有路径点',
    color: '#ff6b6b',
    description: '台风与路径点之间的关系',
    sourceType: NodeType.TYPHOON,
    targetType: NodeType.PATH_POINT,
  },
  [RelationshipType.NEXT]: {
    type: RelationshipType.NEXT,
    label: '路径顺序',
    color: '#4ecdc4',
    description: '路径点之间的顺序关系',
    sourceType: NodeType.PATH_POINT,
    targetType: NodeType.PATH_POINT,
  },
  [RelationshipType.OCCURRED_IN]: {
    type: RelationshipType.OCCURRED_IN,
    label: '发生时间',
    color: '#45b7d1',
    description: '台风与时间节点的关系',
    sourceType: NodeType.TYPHOON,
    targetType: NodeType.TIME,
  },
  [RelationshipType.LANDED_AT]: {
    type: RelationshipType.LANDED_AT,
    label: '登陆地点',
    color: '#96ceb4',
    description: '台风与登陆地点的关系',
    sourceType: NodeType.TYPHOON,
    targetType: NodeType.LOCATION,
    fields: [
      { key: 'land_time', label: '登陆时间', type: 'datetime' },
      { key: 'lat', label: '纬度', type: 'number' },
      { key: 'lon', label: '经度', type: 'number' },
      { key: 'intensity', label: '登陆强度', type: 'string' },
    ],
  },
  // 扩展关系 - 台风生命周期
  [RelationshipType.GENERATED_AT]: {
    type: RelationshipType.GENERATED_AT,
    label: '生成于',
    color: '#74b9ff',
    description: '台风生成位置',
    sourceType: NodeType.TYPHOON,
    targetType: NodeType.LOCATION,
    fields: [
      { key: 'timestamp', label: '生成时间', type: 'datetime' },
      { key: 'lat', label: '纬度', type: 'number' },
      { key: 'lon', label: '经度', type: 'number' },
      { key: 'description', label: '描述', type: 'string' },
    ],
  },
  [RelationshipType.DISSIPATED_AT]: {
    type: RelationshipType.DISSIPATED_AT,
    label: '消散于',
    color: '#a29bfe',
    description: '台风消散位置',
    sourceType: NodeType.TYPHOON,
    targetType: NodeType.LOCATION,
    fields: [
      { key: 'timestamp', label: '消散时间', type: 'datetime' },
      { key: 'lat', label: '纬度', type: 'number' },
      { key: 'lon', label: '经度', type: 'number' },
      { key: 'description', label: '描述', type: 'string' },
    ],
  },
  // 扩展关系 - 强度变化（支持同一台风多次变化到同一强度）
  [RelationshipType.INTENSIFIED_TO]: {
    type: RelationshipType.INTENSIFIED_TO,
    label: '增强为',
    color: '#fd79a8',
    description: '台风强度增强（支持多次增强到同一强度）',
    sourceType: NodeType.TYPHOON,
    targetType: NodeType.INTENSITY,
    fields: [
      { key: 'from_level', label: '原强度等级', type: 'string' },
      { key: 'to_level', label: '目标强度等级', type: 'string' },
      { key: 'change_time', label: '变化时间', type: 'datetime' },
      { key: 'change_sequence', label: '变化序列', type: 'datetime' },
      { key: 'wind_speed_change', label: '风速变化', type: 'number' },
      { key: 'pressure_change', label: '气压变化', type: 'number' },
    ],
  },
  [RelationshipType.WEAKENED_TO]: {
    type: RelationshipType.WEAKENED_TO,
    label: '减弱为',
    color: '#fdcb6e',
    description: '台风强度减弱（支持多次减弱到同一强度）',
    sourceType: NodeType.TYPHOON,
    targetType: NodeType.INTENSITY,
    fields: [
      { key: 'from_level', label: '原强度等级', type: 'string' },
      { key: 'to_level', label: '目标强度等级', type: 'string' },
      { key: 'change_time', label: '变化时间', type: 'datetime' },
      { key: 'change_sequence', label: '变化序列', type: 'datetime' },
      { key: 'wind_speed_change', label: '风速变化', type: 'number' },
      { key: 'pressure_change', label: '气压变化', type: 'number' },
    ],
  },
  // 扩展关系 - 相似性
  [RelationshipType.SIMILAR_TO]: {
    type: RelationshipType.SIMILAR_TO,
    label: '相似于',
    color: '#6c5ce7',
    description: '台风相似性关系',
    sourceType: NodeType.TYPHOON,
    targetType: NodeType.TYPHOON,
    fields: [
      { key: 'similarity_score', label: '相似度分数', type: 'number' },
      { key: 'path_similarity', label: '路径形状相似度', type: 'number' },
      { key: 'genesis_similarity', label: '生成位置相似度', type: 'number' },
      { key: 'intensity_similarity', label: '强度变化相似度', type: 'number' },
      { key: 'temporal_similarity', label: '时间模式相似度', type: 'number' },
    ],
  },
  // 扩展关系 - 地理影响（AFFECTED_AREA 包含经过附近的语义，距离<100km）
  [RelationshipType.AFFECTED_AREA]: {
    type: RelationshipType.AFFECTED_AREA,
    label: '影响区域',
    color: '#e17055',
    description: '台风影响的地理区域（包含经过附近的语义）',
    sourceType: NodeType.TYPHOON,
    targetType: NodeType.LOCATION,
    fields: [
      { key: 'impact_level', label: '影响级别', type: 'string' },
      { key: 'min_distance_km', label: '最小距离(km)', type: 'number' },
      { key: 'passed_at', label: '经过时间', type: 'datetime' },
    ],
  },
};

export const ENTITY_TYPES = Object.values(NODE_TYPE_CONFIG);

export const RELATIONSHIP_TYPES = Object.values(RELATIONSHIP_TYPE_CONFIG);

export const LAYOUT_OPTIONS = [
  { value: 'force', label: '力导向布局' },
  { value: 'circular', label: '环形布局' },
  { value: 'grid', label: '网格布局' },
];

export function getNodeId(nodeType, properties) {
  switch (nodeType) {
    case NodeType.TYPHOON:
      return properties?.typhoon_id || '';
    case NodeType.PATH_POINT:
      return `${properties?.typhoon_id || 'unknown'}_pp_${properties?.sequence || 0}`;
    case NodeType.LOCATION:
      return `location_${properties?.name || 'unknown'}`;
    case NodeType.TIME:
      return `time_${properties?.year || 0}`;
    case NodeType.INTENSITY:
      return `intensity_${properties?.level || 'unknown'}`;
    default:
      return String(Date.now());
  }
}

export function detectNodeType(properties) {
  if (!properties || typeof properties !== 'object') {
    return NodeType.TYPHOON;
  }

  // 台风节点：有typhoon_id和name_cn，但没有sequence
  if ('typhoon_id' in properties && 'name_cn' in properties && !('sequence' in properties)) {
    return NodeType.TYPHOON;
  }
  // 路径点节点：有sequence和lat/lon
  if ('sequence' in properties && 'lat' in properties && 'lon' in properties) {
    return NodeType.PATH_POINT;
  }
  // 地理位置节点：有name和lat/lon，但没有typhoon_id和sequence
  if ('name' in properties && 'lat' in properties && 'lon' in properties && 
      !('typhoon_id' in properties) && !('sequence' in properties)) {
    return NodeType.LOCATION;
  }
  // 时间节点：有year和is_peak_season
  if ('year' in properties && 'is_peak_season' in properties) {
    return NodeType.TIME;
  }
  // 强度等级节点：有level和wind_speed_min
  if ('level' in properties && 'wind_speed_min' in properties) {
    return NodeType.INTENSITY;
  }

  return NodeType.TYPHOON;
}

export function validateRelationship(sourceType, targetType, relationshipType) {
  const validRelationships = [
    // 基础关系
    [NodeType.TYPHOON, NodeType.PATH_POINT, RelationshipType.HAS_PATH_POINT],
    [NodeType.PATH_POINT, NodeType.PATH_POINT, RelationshipType.NEXT],
    [NodeType.TYPHOON, NodeType.TIME, RelationshipType.OCCURRED_IN],
    [NodeType.TYPHOON, NodeType.LOCATION, RelationshipType.LANDED_AT],
    // 扩展关系 - 台风生命周期
    [NodeType.TYPHOON, NodeType.LOCATION, RelationshipType.GENERATED_AT],
    [NodeType.TYPHOON, NodeType.LOCATION, RelationshipType.DISSIPATED_AT],
    // 扩展关系 - 强度变化
    [NodeType.TYPHOON, NodeType.INTENSITY, RelationshipType.INTENSIFIED_TO],
    [NodeType.TYPHOON, NodeType.INTENSITY, RelationshipType.WEAKENED_TO],
    // 扩展关系 - 相似性
    [NodeType.TYPHOON, NodeType.TYPHOON, RelationshipType.SIMILAR_TO],
    // 扩展关系 - 地理影响（AFFECTED_AREA 包含经过附近的语义）
    [NodeType.TYPHOON, NodeType.LOCATION, RelationshipType.AFFECTED_AREA],
  ];

  return validRelationships.some(
    ([s, t, r]) => s === sourceType && t === targetType && r === relationshipType
  );
}

export function transformGraphData(data) {
  if (!data || !data.nodes || !data.links) {
    return { nodes: [], links: [] };
  }

  const transformedNodes = data.nodes.map((node) => {
    const nodeType = node.labels?.[0] || detectNodeType(node.properties);
    const config = NODE_TYPE_CONFIG[nodeType] || NODE_TYPE_CONFIG[NodeType.TYPHOON];

    return {
      id: node.id,
      labels: node.labels || [nodeType],
      category: nodeType,
      name: node.properties?.name_cn || node.properties?.name || node.id,
      symbolSize: config.symbolSize,
      itemStyle: {
        color: config.color,
      },
      properties: node.properties || {},
    };
  });

  const transformedLinks = data.links.map((link) => {
    const relConfig = RELATIONSHIP_TYPE_CONFIG[link.type] || {};

    return {
      source: link.source,
      target: link.target,
      type: link.type,
      relation: relConfig.label || link.type,
      properties: link.properties || {},
      lineStyle: {
        color: relConfig.color || '#999',
      },
    };
  });

  return {
    nodes: transformedNodes,
    links: transformedLinks,
  };
}

export function formatNodeTooltip(node) {
  const nodeType = node.category || node.labels?.[0];
  const config = NODE_TYPE_CONFIG[nodeType] || NODE_TYPE_CONFIG[NodeType.TYPHOON];

  let html = `<div style="padding: 10px; max-width: 300px;">`;
  html += `<div style="font-weight: bold; font-size: 14px; margin-bottom: 8px; color: ${config.color}">`;
  html += `${node.name || node.id}</div>`;
  html += `<div style="color: #666; font-size: 12px; margin-bottom: 8px;">类型: ${config.label}</div>`;

  // 使用配置的字段定义来格式化显示
  if (config.fields && node.properties) {
    config.fields.forEach(field => {
      const value = node.properties[field.key];
      if (value !== null && value !== undefined) {
        let displayValue = value;
        // 格式化日期时间
        if (field.type === 'datetime' && typeof value === 'number') {
          displayValue = new Date(value).toLocaleString('zh-CN');
        }
        // 格式化数字
        if (field.type === 'number' && typeof value === 'number') {
          displayValue = value.toFixed(2);
        }
        html += `<div style="color: #888; font-size: 11px; margin-top: 4px;">${field.label}: ${displayValue}</div>`;
      }
    });
  } else if (node.properties) {
    // 回退到默认显示
    Object.entries(node.properties).forEach(([key, value]) => {
      if (value !== null && value !== undefined && key !== 'name' && key !== 'typhoon_id') {
        html += `<div style="color: #888; font-size: 11px; margin-top: 4px;">${key}: ${value}</div>`;
      }
    });
  }
  html += `</div>`;
  return html;
}

export function formatEdgeTooltip(edge) {
  const relConfig = RELATIONSHIP_TYPE_CONFIG[edge.type] || {};
  const label = relConfig.label || edge.type || '未知关系';

  return `<div style="padding: 8px;">
    <div style="font-weight: bold;">${label}</div>
    ${relConfig.description ? `<div style="color: #888; font-size: 11px;">${relConfig.description}</div>` : ''}
  </div>`;
}

export default {
  NodeType,
  RelationshipType,
  IntensityLevel,
  INTENSITY_LEVELS,
  NODE_TYPE_CONFIG,
  RELATIONSHIP_TYPE_CONFIG,
  ENTITY_TYPES,
  RELATIONSHIP_TYPES,
  LAYOUT_OPTIONS,
  getNodeId,
  detectNodeType,
  validateRelationship,
  transformGraphData,
  formatNodeTooltip,
  formatEdgeTooltip,
};
