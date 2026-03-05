# AIAgent GraphRAG LocalSearch 开发方案

## 一、需求分析

### 1.1 目标

在保留现有检索结果可视化功能的基础上，使用 **GraphRAG** 技术，利用已构建的Neo4j知识图谱进行 **LocalSearch** 来回答问题。

### 1.2 GraphRAG vs 传统RAG

| 特性       | 传统RAG        | GraphRAG            |
| ---------- | -------------- | ------------------- |
| 数据结构   | 文本块/向量    | 图结构（节点+关系） |
| 检索方式   | 向量相似度搜索 | 图遍历+语义搜索     |
| 上下文理解 | 局部文本片段   | 实体关系网络        |
| 推理能力   | 有限           | 支持多跳推理        |
| 可解释性   | 较低           | 高（可视化图谱）    |

### 1.3 LocalSearch 核心思想

LocalSearch是GraphRAG中的一种查询策略，它从知识图谱中的特定实体出发，通过遍历相关关系和邻居节点，收集与查询相关的局部子图信息，然后将这些信息作为上下文提供给LLM进行回答。

### 1.4 关键设计决策

#### 1.4.1 关键词提取策略（优化点）

**问题1解答：LocalSearch本身有关键词提取能力，前端关键词提取是否必要？**

| 方案             | 说明                                           | 建议                  |
| ---------------- | ---------------------------------------------- | --------------------- |
| **前端提取**     | 前端提取关键词，后端直接用于种子实体定位       | ❌ 不推荐，重复工作   |
| **后端统一提取** | 后端GraphRAG服务统一处理实体识别和链接         | ✅ **推荐**，职责清晰 |
| **混合策略**     | 前端轻量预提取用于UI展示，后端深度提取用于检索 | ⚠️ 可选，增加复杂度   |

**推荐方案：后端统一提取**

- **原因1**：LocalSearch的核心是"实体链接"而非"关键词匹配"，需要将自然语言映射到图谱实体ID
- **原因2**：后端可以访问Neo4j全文索引，进行更准确的语义匹配
- **原因3**：避免前后端重复实现，减少维护成本
- **原因4**：后端提取后可以立即进行子图遍历，流程更高效

**前端职责简化**：

- 仅保留**检索判断逻辑**（判断是否需要调用GraphRAG）
- 移除**关键词提取逻辑**
- 将原始查询直接发送给后端GraphRAG服务

#### 1.4.2 检索判断逻辑优化（优化点）

**问题2解答：如何优化检索判断逻辑使回答流程更高效？**

**原方案问题**：

- 判断逻辑复杂，需要维护大量关键词和正则表达式
- 判断和检索分离，增加一次网络请求
- 某些边界情况判断不准确

**优化方案：智能分层判断 + 快速失败机制**

```
用户提问
    ↓
【第一层】轻量级预判断（前端）
    - 仅检查是否包含台风相关关键词（简单字符串匹配）
    - 耗时 < 1ms
    - 如果不相关，直接走普通AI问答
    ↓
【第二层】GraphRAG检索（后端）
    - 尝试进行实体链接
    - 如果链接失败（找不到相关实体），快速返回，降级到普通搜索
    - 如果链接成功，继续子图遍历
    ↓
【第三层】结果质量评估（后端）
    - 评估检索到的子图质量（节点数、关系丰富度）
    - 如果质量低，补充传统搜索或降级
    ↓
生成回答
```

**优化后的判断逻辑特点**：

1. **前端轻量**：只负责快速过滤明显不相关的查询
2. **后端智能**：实体链接失败时快速降级，不浪费资源
3. **质量评估**：确保只有高质量的图谱上下文才用于增强回答

## 二、技术架构设计

### 2.1 优化后的整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户提问                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  【第一层】前端轻量级预判断（< 1ms）                                          │
│   - 简单关键词匹配（台风、登陆、风速等核心词）                                │
│   - 快速过滤明显不相关的查询（如"你好"、"谢谢"）                              │
│   - 如果判断不相关 → 直接走普通AI问答（跳过GraphRAG）                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓ 判断相关
┌─────────────────────────────────────────────────────────────────────────────┐
│  【第二层】后端GraphRAG智能检索                                               │
│                                                                               │
│  2.1 实体链接（Entity Linking）                                               │
│      - 使用全文索引进行语义匹配                                               │
│      - 如果链接失败 → 快速降级到传统搜索                                      │
│                              ↓ 链接成功                                       │
│  2.2 种子实体选择（Seed Selection）                                           │
│      - 选择高置信度的种子节点                                                 │
│      - 支持多种子节点（复杂查询）                                             │
│                              ↓                                                │
│  2.3 局部子图遍历（Local Subgraph Traversal）                                 │
│      - 从种子出发，遍历指定深度的邻居                                         │
│      - 使用APOC进行高效图遍历                                                 │
│                              ↓                                                │
│  2.4 结果质量评估（Quality Assessment）                                       │
│      - 评估子图质量（节点数、关系丰富度）                                     │
│      - 如果质量低 → 补充传统搜索或降级                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓ 质量合格
┌─────────────────────────────────────────────────────────────────────────────┐
│  【第三层】上下文生成与回答                                                   │
│                                                                               │
│  3.1 上下文生成（Context Assembly）                                           │
│      - 将子图转换为结构化文本                                                 │
│      - 生成推理路径描述                                                       │
│                              ↓                                                │
│  3.2 LLM回答生成                                                              │
│      - 使用增强Prompt（问题+图谱上下文）                                      │
│      - 调用AI模型生成回答                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  【第四层】前端可视化展示                                                     │
│   - 展示检索到的局部子图                                                      │
│   - 显示种子实体、推理路径、遍历统计                                          │
│   - 支持交互式探索                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

**架构优化要点**：

1. **前端简化**：只保留轻量级预判断，移除复杂的关键词提取
2. **后端统一**：实体识别、链接、遍历、质量评估全部在后端完成
3. **快速失败**：实体链接失败或子图质量低时，快速降级不阻塞流程
4. **质量优先**：只有高质量的图谱上下文才用于增强回答

### 2.2 核心组件

#### 2.2.1 实体识别器（Entity Recognizer）

- 基于规则+模型的混合实体识别
- 识别台风名称、地理位置、时间、强度等级等
- 将自然语言查询映射到图谱实体

#### 2.2.2 种子选择器（Seed Selector）

- 根据实体识别结果选择种子节点
- 支持多种子节点（复杂查询）
- 计算实体与查询的匹配分数

#### 2.2.3 子图遍历器（Subgraph Traverser）

- 实现BFS/DFS图遍历算法
- 支持关系过滤（只遍历特定类型关系）
- 控制遍历深度和广度

#### 2.2.4 上下文组装器（Context Assembler）

- 将图数据转换为文本描述
- 实现上下文压缩和去重
- 支持多种输出格式（结构化文本、JSON、自然语言）

## 三、后端API设计

### 3.1 新增API接口

#### 3.1.1 GraphRAG LocalSearch 接口

```python
# POST /api/kg/graphrag/search
class GraphRAGSearchRequest(BaseModel):
    """GraphRAG搜索请求"""
    query: str = Field(..., description="用户查询")
    seed_entities: Optional[List[str]] = Field(default=None, description="指定的种子实体")
    max_depth: int = Field(default=2, ge=1, le=4, description="遍历深度")
    max_nodes: int = Field(default=50, ge=10, le=200, description="最大节点数")
    relationship_types: Optional[List[str]] = Field(default=None, description="关系类型过滤")
    include_paths: bool = Field(default=True, description="是否包含路径信息")
    context_format: Literal["text", "structured", "cypher"] = Field(default="text", description="上下文格式")

class GraphRAGSearchResponse(BaseModel):
    """GraphRAG搜索响应"""
    query: str
    seed_entities: List[Dict]  # 种子实体信息
    subgraph: GraphData  # 局部子图数据
    context_text: str  # 生成的上下文文本
    context_structured: Dict  # 结构化上下文
    traversal_stats: Dict  # 遍历统计信息
    related_questions: List[str]  # 相关问题建议
```

#### 3.1.2 实体链接接口

```python
# POST /api/kg/graphrag/entity_linking
class EntityLinkingRequest(BaseModel):
    """实体链接请求"""
    query: str
    entity_types: Optional[List[str]] = Field(default=["Typhoon", "Location"])
    top_k: int = Field(default=5)

class EntityLinkingResponse(BaseModel):
    """实体链接响应"""
    query: str
    entities: List[LinkedEntity]

class LinkedEntity(BaseModel):
    """链接的实体"""
    mention: str  # 查询中的提及文本
    entity_id: str  # 图谱中的实体ID
    entity_type: str  # 实体类型
    entity_name: str  # 实体名称
    score: float  # 匹配分数
    properties: Dict  # 实体属性
```

#### 3.1.3 多跳推理接口

```python
# POST /api/kg/graphrag/multi_hop
class MultiHopRequest(BaseModel):
    """多跳推理请求"""
    start_entity: str
    end_entity: Optional[str] = None
    query: str
    max_hops: int = Field(default=3, ge=1, le=5)
    relationship_filter: Optional[List[str]] = None

class MultiHopResponse(BaseModel):
    """多跳推理响应"""
    paths: List[GraphPath]  # 找到的路径
    reasoning_context: str  # 推理上下文

class GraphPath(BaseModel):
    """图路径"""
    nodes: List[Dict]
    relationships: List[Dict]
    path_score: float
    path_description: str
```

### 3.2 Cypher查询设计

#### 3.2.1 局部子图遍历查询

```cypher
// 从种子实体出发，遍历局部子图
MATCH (seed:Typhoon)
WHERE seed.typhoon_id IN $seed_ids OR seed.name_cn IN $seed_names
WITH seed

// 遍历指定深度的邻居
CALL apoc.path.subgraphAll(seed, {
    relationshipFilter: $rel_filter,  // 关系类型过滤
    minLevel: 1,
    maxLevel: $max_depth,
    limit: $max_nodes
}) YIELD nodes, relationships

// 返回子图数据
RETURN {
    seed: seed,
    nodes: nodes,
    relationships: relationships,
    node_count: size(nodes),
    rel_count: size(relationships)
} as subgraph
```

#### 3.2.2 实体语义搜索

```cypher
// 基于名称相似度的实体搜索
CALL db.index.fulltext.queryNodes("entitySearch", $query)
YIELD node, score
WHERE score > $min_score
WITH node, score
ORDER BY score DESC
LIMIT $limit

RETURN {
    entity_id: CASE
        WHEN node:Typhoon THEN node.typhoon_id
        WHEN node:Location THEN 'loc_' + node.name
        ELSE id(node)
    END,
    entity_type: labels(node)[0],
    name: CASE
        WHEN node:Typhoon THEN coalesce(node.name_cn, node.name_en, node.typhoon_id)
        WHEN node:Location THEN node.name
        ELSE coalesce(node.name, node.id)
    END,
    properties: properties(node),
    score: score
} as entity
```

#### 3.2.3 路径发现查询

```cypher
// 发现两个实体之间的路径
MATCH path = shortestPath(
    (start:Typhoon {typhoon_id: $start_id})-[*1..5]-(end:Typhoon {typhoon_id: $end_id})
)
WHERE ALL(r IN relationships(path) WHERE type(r) IN $allowed_rels)

WITH path,
     [n IN nodes(path) | {
         id: CASE WHEN n:Typhoon THEN n.typhoon_id
                  WHEN n:Location THEN 'loc_' + n.name
                  ELSE id(n) END,
         type: labels(n)[0],
         name: coalesce(n.name_cn, n.name, n.typhoon_id)
     }] as path_nodes,
     [r IN relationships(path) | {
         type: type(r),
         properties: properties(r)
     }] as path_rels

RETURN {
    path_length: length(path),
    nodes: path_nodes,
    relationships: path_rels,
    path_description: apoc.text.join(
        [i IN range(0, size(path_nodes)-2) |
         path_nodes[i].name + ' -[' + path_rels[i].type + ']-> ' + path_nodes[i+1].name
        ], ' -> '
    )
} as path_info
```

## 四、上下文生成策略

### 4.1 文本上下文生成

```python
def generate_text_context(subgraph: GraphData, query: str) -> str:
    """将子图转换为文本上下文"""

    context_parts = []

    # 1. 实体描述
    for node in subgraph.nodes:
        if node.type == "Typhoon":
            context_parts.append(
                f"台风 {node.properties.get('name_cn', node.id)} "
                f"({node.id}) 发生于{node.properties.get('year', '未知')}年，"
                f"最大风速{node.properties.get('max_wind_speed', '未知')}m/s，"
                f"最低气压{node.properties.get('min_pressure', '未知')}hPa。"
            )
        elif node.type == "Location":
            context_parts.append(
                f"地点 {node.properties.get('name', node.id)} "
                f"位于({node.properties.get('lat', '?')}, {node.properties.get('lon', '?')})。"
            )

    # 2. 关系描述
    for rel in subgraph.relationships:
        if rel.type == "LANDED_AT":
            context_parts.append(
                f"{rel.source} 在 {rel.properties.get('land_time', '未知时间')} "
                f"登陆 {rel.target}，登陆时强度为{rel.properties.get('intensity', '未知')}。"
            )
        elif rel.type == "SIMILAR_TO":
            context_parts.append(
                f"{rel.source} 与 {rel.target} 相似度为 "
                f"{rel.properties.get('similarity_score', '?')}。"
            )

    # 3. 统计信息
    context_parts.append(
        f"\n检索统计：共找到 {len(subgraph.nodes)} 个实体，"
        f"{len(subgraph.relationships)} 个关系。"
    )

    return "\n".join(context_parts)
```

### 4.2 结构化上下文生成

```python
def generate_structured_context(subgraph: GraphData) -> Dict:
    """生成结构化上下文，便于LLM理解"""

    return {
        "entities": {
            "typhoons": [
                {
                    "id": node.id,
                    "name": node.properties.get("name_cn"),
                    "year": node.properties.get("year"),
                    "max_wind_speed": node.properties.get("max_wind_speed"),
                    "min_pressure": node.properties.get("min_pressure"),
                    "intensity": node.properties.get("peak_intensity")
                }
                for node in subgraph.nodes if node.type == "Typhoon"
            ],
            "locations": [
                {
                    "id": node.id,
                    "name": node.properties.get("name"),
                    "lat": node.properties.get("lat"),
                    "lon": node.properties.get("lon")
                }
                for node in subgraph.nodes if node.type == "Location"
            ]
        },
        "relationships": [
            {
                "source": rel.source,
                "target": rel.target,
                "type": rel.type,
                "properties": rel.properties
            }
            for rel in subgraph.relationships
        ],
        "paths": [
            # 关键路径信息
        ]
    }
```

## 五、前端集成方案

### 5.1 修改 KnowledgeGraphPanel 组件

增强现有的 KnowledgeGraphPanel 组件，支持展示 GraphRAG 的检索结果：

```jsx
const KnowledgeGraphPanel = ({
  isVisible,
  searchResults,
  graphContext,
  onClose,
  isLoading,
  // 新增GraphRAG相关props
  traversalStats,
  seedEntities,
  reasoningPaths,
}) => {
  const [activeTab, setActiveTab] = useState("visualization");

  return (
    <div className={`knowledge-graph-panel ${isVisible ? "visible" : ""}`}>
      {/* 头部 */}
      <div className="panel-header">
        <h3>GraphRAG 检索结果</h3>
        {traversalStats && (
          <Tag color="blue">
            {traversalStats.node_count}节点 / {traversalStats.rel_count}关系
          </Tag>
        )}
      </div>

      {/* 标签页 */}
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="子图可视化" key="visualization">
          <GraphVisualization
            subgraph={searchResults}
            seedEntities={seedEntities}
            paths={reasoningPaths}
          />
        </TabPane>

        <TabPane tab="推理路径" key="paths">
          <ReasoningPaths paths={reasoningPaths} />
        </TabPane>

        <TabPane tab="上下文" key="context">
          <ContextDisplay context={graphContext} />
        </TabPane>

        <TabPane tab="种子实体" key="seeds">
          <SeedEntities entities={seedEntities} />
        </TabPane>
      </Tabs>
    </div>
  );
};
```

### 5.2 新增 GraphRAG API 调用

```javascript
// api.js

/**
 * GraphRAG LocalSearch
 */
export async function graphRAGLocalSearch(query, options = {}) {
  const response = await fetch(`${API_BASE_URL}/api/kg/graphrag/search`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      query,
      max_depth: options.maxDepth || 2,
      max_nodes: options.maxNodes || 50,
      include_paths: true,
      context_format: "text",
      ...options,
    }),
  });
  return handleResponse(response);
}

/**
 * 实体链接
 */
export async function linkEntities(query, options = {}) {
  const response = await fetch(
    `${API_BASE_URL}/api/kg/graphrag/entity_linking`,
    {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        query,
        entity_types: options.entityTypes || ["Typhoon", "Location"],
        top_k: options.topK || 5,
      }),
    },
  );
  return handleResponse(response);
}

/**
 * 多跳推理
 */
export async function multiHopReasoning(startEntity, query, options = {}) {
  const response = await fetch(`${API_BASE_URL}/api/kg/graphrag/multi_hop`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      start_entity: startEntity,
      query,
      max_hops: options.maxHops || 3,
      ...options,
    }),
  });
  return handleResponse(response);
}
```

### 5.3 修改 AIAgent.jsx 集成 GraphRAG（优化版）

#### 5.3.1 优化后的轻量级检索判断逻辑

```javascript
/**
 * 【优化】轻量级检索判断 - 仅用于快速过滤
 * 移除复杂的关键词提取，只保留简单的相关性判断
 */
const shouldUseKnowledgeRetrieval = useCallback((question) => {
  // 极简核心关键词列表（仅用于快速判断）
  const coreKeywords = [
    "台风",
    "飓风",
    "气旋",
    "热带风暴",
    "热带低压",
    "登陆",
    "路径",
    "风速",
    "气压",
    "强度",
  ];

  // 地理位置关键词（快速匹配）
  const locationKeywords = [
    "广东",
    "福建",
    "浙江",
    "海南",
    "台湾",
    "香港",
    "澳门",
    "广西",
    "江苏",
    "上海",
    "山东",
  ];

  // 简单字符串包含检查（性能最优）
  const hasCoreKeyword = coreKeywords.some((kw) => question.includes(kw));
  const hasLocationKeyword = locationKeywords.some((kw) =>
    question.includes(kw),
  );

  // 时间模式（年份）
  const hasYearPattern = /\b(19|20)\d{2}\b/.test(question);

  // 判断逻辑：核心词 + (地点或年份)
  return (
    hasCoreKeyword &&
    (hasLocationKeyword || hasYearPattern || question.includes("台风"))
  );
}, []);

/**
 * 【移除】原有的复杂关键词提取逻辑
 * 原因：GraphRAG后端会统一处理实体识别和链接
 */
// const extractSearchKeywords = useCallback((question) => { ... }); // 已移除
```

#### 5.3.2 优化后的消息处理流程

```javascript
const handleQuestionClick = useCallback(
  async (questionText) => {
    // ... 原有代码：添加用户消息 ...

    // 【优化】第一步：轻量级预判断
    const needsKnowledge = shouldUseKnowledgeRetrieval(questionText);

    if (!needsKnowledge) {
      // 快速路径：直接走普通AI问答
      console.log("🚀 快速路径：直接AI问答");
      await sendToAI(questionText);
      return;
    }

    // 【优化】第二步：调用GraphRAG（后端统一处理实体识别和检索）
    setIsSearchingKnowledge(true);
    let enhancedPrompt = questionText;

    try {
      console.log("🔍 调用GraphRAG LocalSearch...");

      // 直接发送原始查询，后端处理所有逻辑
      const graphRAGResult = await graphRAGLocalSearch(questionText, {
        maxDepth: 2,
        maxNodes: 50,
        includePaths: true,
        enableQualityCheck: true, // 启用质量评估
      });

      // 【优化】第三步：根据后端返回的质量评估结果决定如何使用
      if (graphRAGResult.quality_score >= 0.6) {
        // 高质量结果：使用GraphRAG上下文增强
        console.log("✅ GraphRAG高质量结果，使用图谱上下文");

        setGraphContext({
          text: graphRAGResult.context_text,
          structured: graphRAGResult.context_structured,
          seedEntities: graphRAGResult.seed_entities,
        });

        setKnowledgeSearchResults(graphRAGResult.subgraph);
        setSeedEntities(graphRAGResult.seed_entities);
        setTraversalStats(graphRAGResult.traversal_stats);
        setReasoningPaths(graphRAGResult.reasoning_paths || []);
        setShowKnowledgePanel(true);

        enhancedPrompt = buildGraphRAGPrompt(questionText, graphRAGResult);
      } else if (graphRAGResult.quality_score >= 0.3) {
        // 中等质量：GraphRAG + 传统搜索混合
        console.log("⚠️ GraphRAG中等质量，混合使用");

        const fallbackResult = await searchKnowledgeGraph(questionText, 10);
        enhancedPrompt = buildHybridPrompt(
          questionText,
          graphRAGResult,
          fallbackResult,
        );

        // 仍然展示可视化，但标记为"部分结果"
        setKnowledgeSearchResults(graphRAGResult.subgraph);
        setShowKnowledgePanel(true);
      } else {
        // 低质量：降级到传统搜索
        console.log("📉 GraphRAG质量低，降级到传统搜索");

        const fallbackResult = await searchKnowledgeGraph(questionText, 20);
        enhancedPrompt = buildFallbackPrompt(questionText, fallbackResult);

        // 可选：展示传统搜索结果
        if (fallbackResult?.length > 0) {
          setKnowledgeSearchResults({ typhoons: fallbackResult });
          setShowKnowledgePanel(true);
        }
      }
    } catch (error) {
      console.error("❌ GraphRAG检索失败:", error);
      // 异常降级
      const fallbackResult = await searchKnowledgeGraph(questionText, 20);
      enhancedPrompt = buildFallbackPrompt(questionText, fallbackResult);
    } finally {
      setIsSearchingKnowledge(false);
    }

    // 发送AI请求
    await sendToAI(enhancedPrompt);
  },
  [shouldUseKnowledgeRetrieval /* 其他依赖 */],
);
```

#### 5.3.3 后端质量评估机制

```python
# backend/app/services/graphrag/quality_assessor.py

class ResultQualityAssessor:
    """GraphRAG结果质量评估器"""

    def assess_quality(self, subgraph: GraphData, seed_entities: List[Dict]) -> Dict:
        """
        评估检索结果质量

        Returns:
            {
                "score": float,  # 0-1质量分数
                "level": str,    # "high" | "medium" | "low"
                "factors": Dict, # 各维度评分
                "suggestion": str # 改进建议
            }
        """
        factors = {}

        # 1. 节点数量评分（理想范围：10-50）
        node_count = len(subgraph.nodes)
        factors["node_count"] = self._score_node_count(node_count)

        # 2. 关系丰富度评分
        rel_count = len(subgraph.relationships)
        factors["relationship_richness"] = self._score_relationships(rel_count, node_count)

        # 3. 种子实体匹配度
        factors["seed_match"] = self._score_seed_match(seed_entities)

        # 4. 实体类型多样性
        factors["type_diversity"] = self._score_type_diversity(subgraph.nodes)

        # 5. 属性完整度
        factors["attribute_completeness"] = self._score_attribute_completeness(subgraph.nodes)

        # 计算总分（加权平均）
        weights = {
            "node_count": 0.25,
            "relationship_richness": 0.25,
            "seed_match": 0.20,
            "type_diversity": 0.15,
            "attribute_completeness": 0.15
        }

        total_score = sum(
            factors[key] * weights[key]
            for key in weights.keys()
        )

        # 确定质量等级
        if total_score >= 0.7:
            level = "high"
        elif total_score >= 0.4:
            level = "medium"
        else:
            level = "low"

        return {
            "score": round(total_score, 2),
            "level": level,
            "factors": factors,
            "suggestion": self._generate_suggestion(factors, level)
        }

    def _score_node_count(self, count: int) -> float:
        """节点数量评分"""
        if 10 <= count <= 50:
            return 1.0
        elif 5 <= count < 10:
            return 0.7
        elif 50 < count <= 100:
            return 0.8
        elif count < 5:
            return 0.3
        else:
            return 0.5

    def _score_relationships(self, rel_count: int, node_count: int) -> float:
        """关系丰富度评分"""
        if node_count == 0:
            return 0.0

        # 理想的关系密度：每个节点2-5个关系
        density = rel_count / node_count

        if 2 <= density <= 5:
            return 1.0
        elif 1 <= density < 2:
            return 0.7
        elif density > 5:
            return 0.8
        else:
            return 0.4

    def _score_seed_match(self, seed_entities: List[Dict]) -> float:
        """种子实体匹配度评分"""
        if not seed_entities:
            return 0.0

        # 基于种子实体的置信度计算
        avg_confidence = sum(e.get("score", 0) for e in seed_entities) / len(seed_entities)
        return avg_confidence

    def _score_type_diversity(self, nodes: List[GraphNode]) -> float:
        """实体类型多样性评分"""
        types = set(node.type for node in nodes)

        # 期望包含多种类型：Typhoon, Location, Time, Intensity等
        if len(types) >= 4:
            return 1.0
        elif len(types) >= 2:
            return 0.7
        else:
            return 0.4

    def _score_attribute_completeness(self, nodes: List[GraphNode]) -> float:
        """属性完整度评分"""
        if not nodes:
            return 0.0

        # 检查关键属性的完整度
        total_score = 0
        for node in nodes:
            if node.type == "Typhoon":
                # 台风节点期望有：name_cn, year, max_wind_speed等
                required_attrs = ["name_cn", "year", "max_wind_speed"]
                present = sum(1 for attr in required_attrs if node.properties.get(attr))
                total_score += present / len(required_attrs)
            else:
                total_score += 0.5  # 其他类型默认中等评分

        return total_score / len(nodes)

    def _generate_suggestion(self, factors: Dict, level: str) -> str:
        """生成改进建议"""
        if level == "high":
            return "质量良好，可直接使用"

        suggestions = []

        if factors.get("node_count", 1) < 0.5:
            suggestions.append("节点数量过少，建议扩大遍历深度")

        if factors.get("relationship_richness", 1) < 0.5:
            suggestions.append("关系稀疏，建议放宽关系类型过滤")

        if factors.get("seed_match", 1) < 0.5:
            suggestions.append("种子实体匹配度低，建议检查查询表述")

        return "; ".join(suggestions) if suggestions else "建议补充传统搜索"
```

#### 5.3.4 优化后的Prompt构建

```javascript
/**
 * 构建GraphRAG增强Prompt
 */
function buildGraphRAGPrompt(originalQuestion, graphRAGResult) {
  let prompt = originalQuestion;

  prompt += "\n\n[基于知识图谱的检索结果]\n";
  prompt += `质量评分：${graphRAGResult.quality_score}/1.0\n\n`;

  // 种子实体
  if (graphRAGResult.seed_entities?.length > 0) {
    prompt += "检索到的关键实体：\n";
    graphRAGResult.seed_entities.forEach((entity) => {
      prompt += `- ${entity.entity_name} (${entity.entity_type}, 置信度: ${entity.score})\n`;
    });
    prompt += "\n";
  }

  // 上下文
  if (graphRAGResult.context_text) {
    prompt += "相关背景信息：\n";
    prompt += graphRAGResult.context_text;
    prompt += "\n\n";
  }

  // 推理路径
  if (graphRAGResult.reasoning_paths?.length > 0) {
    prompt += "推理路径：\n";
    graphRAGResult.reasoning_paths.slice(0, 3).forEach((path, idx) => {
      prompt += `${idx + 1}. ${path.path_description}\n`;
    });
    prompt += "\n";
  }

  prompt += "请基于以上知识图谱信息回答问题。";

  return prompt;
}

/**
 * 构建混合Prompt（GraphRAG + 传统搜索）
 */
function buildHybridPrompt(originalQuestion, graphRAGResult, fallbackResult) {
  let prompt = buildGraphRAGPrompt(originalQuestion, graphRAGResult);

  prompt += "\n\n[补充检索结果]\n";
  prompt += "以下是通过传统搜索找到的额外相关信息：\n";

  fallbackResult.slice(0, 5).forEach((item, idx) => {
    prompt += `${idx + 1}. ${item.name_cn || item.typhoon_id} (${item.year}年)\n`;
  });

  return prompt;
}

/**
 * 构建降级Prompt（仅传统搜索）
 */
function buildFallbackPrompt(originalQuestion, fallbackResult) {
  let prompt = originalQuestion;

  if (fallbackResult?.length > 0) {
    prompt += "\n\n[检索结果]\n";
    prompt += "以下是相关台风信息：\n";

    fallbackResult.slice(0, 10).forEach((item, idx) => {
      prompt += `${idx + 1}. ${item.name_cn || item.typhoon_id} `;
      prompt += `(${item.year}年, 最大风速${item.max_wind_speed}m/s)\n`;
    });

    prompt += "\n请基于以上信息回答问题。";
  }

  return prompt;
}
```

## 六、实现可行性分析

### 6.1 可行性评估

| 需求             | 可行性  | 说明                                      |
| ---------------- | ------- | ----------------------------------------- |
| 使用GraphRAG技术 | ✅ 可行 | 已有Neo4j知识图谱，具备实现基础           |
| LocalSearch检索  | ✅ 可行 | 可通过Cypher的`apoc.path.subgraphAll`实现 |
| 保留可视化功能   | ✅ 可行 | 现有KnowledgeGraphPanel可直接复用并增强   |
| 实体链接         | ✅ 可行 | 可结合全文索引和规则匹配实现              |
| 多跳推理         | ✅ 可行 | Neo4j的`shortestPath`和路径扩展支持       |

### 6.2 技术依赖

1. **Neo4j APOC插件**：用于高级图遍历（`apoc.path.subgraphAll`）
2. **全文索引**：用于实体语义搜索
3. **后端FastAPI**：需要新增GraphRAG相关API
4. **前端React**：增强现有组件

### 6.3 性能考虑

| 优化点       | 策略                     |
| ------------ | ------------------------ |
| 遍历深度控制 | 默认深度2，最大深度4     |
| 节点数量限制 | 默认50个，最大200个      |
| 查询超时     | 设置5秒超时机制          |
| 缓存策略     | 缓存常见查询的子图结果   |
| 异步处理     | 图遍历使用异步Cypher查询 |

## 七、实施步骤

### 步骤1：后端GraphRAG服务开发

1. 创建 `backend/app/services/graphrag/` 目录
2. 实现 `entity_linker.py` - 实体链接服务
3. 实现 `subgraph_traverser.py` - 子图遍历服务
4. 实现 `context_generator.py` - 上下文生成服务
5. 实现 `graphrag_engine.py` - GraphRAG主引擎
6. 在 `knowledge_graph.py` 中添加新的API路由

### 步骤2：前端API集成

1. 在 `api.js` 中添加 GraphRAG 相关API调用
2. 修改 `KnowledgeGraphPanel` 组件，增强展示功能
3. 修改 `AIAgent.jsx`，集成 GraphRAG 调用流程

### 步骤3：测试与优化

1. 单元测试各个服务组件
2. 集成测试端到端流程
3. 性能测试和优化
4. 用户体验测试

## 八、预期效果

### 8.1 功能提升

| 方面       | 传统搜索   | GraphRAG LocalSearch |
| ---------- | ---------- | -------------------- |
| 上下文理解 | 关键词匹配 | 实体关系网络         |
| 推理能力   | 单跳查询   | 多跳推理             |
| 可解释性   | 低         | 高（可视化路径）     |
| 回答准确性 | 一般       | 更高（结构化上下文） |

### 8.2 用户体验

1. **更精准的回答**：基于图结构的上下文，AI能给出更准确的台风相关信息
2. **可视化推理过程**：用户可以看到的检索路径和推理过程
3. **交互式探索**：用户可以点击图谱节点进行进一步探索
4. **智能建议**：系统可以根据子图推荐相关问题

---

## 附录A：优化前后对比总结

### A.1 问题解答

#### 问题1：LocalSearch本身有关键词提取能力，当前的关键词提取是否有必要保留？

**答案：不需要保留复杂的前端关键词提取，改为后端统一处理**

| 维度           | 优化前                     | 优化后                                 |
| -------------- | -------------------------- | -------------------------------------- |
| **职责划分**   | 前端提取关键词 → 后端检索  | 前端仅判断 → 后端统一处理实体识别+检索 |
| **实现复杂度** | 高（前后端重复逻辑）       | 低（后端单一职责）                     |
| **准确性**     | 中（前端无法访问全文索引） | 高（后端语义匹配更准确）               |
| **维护成本**   | 高（两处修改）             | 低（一处修改）                         |
| **性能**       | 多一次网络传输             | 直接调用，更高效                       |

**优化原因**：

1. GraphRAG的核心是"实体链接"而非"关键词匹配"
2. 后端可以访问Neo4j全文索引，进行更准确的语义匹配
3. 避免前后端重复实现，减少维护成本
4. 后端提取后可以立即进行子图遍历，流程更高效

#### 问题2：如何优化检索判断逻辑使回答流程更加高效？

**答案：采用"智能分层判断 + 快速失败机制"**

| 层级               | 优化前              | 优化后               | 效果                |
| ------------------ | ------------------- | -------------------- | ------------------- |
| **第一层（前端）** | 复杂关键词+正则匹配 | 极简核心词匹配       | 耗时从~10ms降至~1ms |
| **第二层（后端）** | 直接执行检索        | 实体链接失败快速返回 | 无效查询节省~500ms  |
| **第三层（后端）** | 无质量评估          | 质量评分+智能降级    | 低质量结果自动补充  |
| **整体流程**       | 同步阻塞            | 异步+快速失败        | 响应速度提升30-50%  |

### A.2 架构优化对比

```
【优化前】
用户提问 → 前端复杂判断 → 前端提取关键词 → 发送后端 → 后端检索 → 返回结果
              ↑______________↑
              重复工作，增加延迟

【优化后】
用户提问 → 前端轻量判断 → 发送后端 → 后端实体链接 → 成功→子图遍历→质量评估→返回
                                    ↓ 失败
                              快速降级到传统搜索
```

### A.3 质量评估机制

**新增质量评估维度**：

| 维度       | 权重 | 评估标准             |
| ---------- | ---- | -------------------- |
| 节点数量   | 25%  | 理想范围10-50个      |
| 关系丰富度 | 25%  | 理想密度2-5关系/节点 |
| 种子匹配度 | 20%  | 实体链接置信度       |
| 类型多样性 | 15%  | 期望4种以上实体类型  |
| 属性完整度 | 15%  | 关键属性填充率       |

**质量分级处理**：

| 质量分数 | 等级 | 处理方式                |
| -------- | ---- | ----------------------- |
| ≥0.7     | 高   | 直接使用GraphRAG上下文  |
| 0.3-0.7  | 中   | GraphRAG + 传统搜索混合 |
| <0.3     | 低   | 降级到传统搜索          |

### A.4 性能优化效果预估

| 指标             | 优化前 | 优化后   | 提升       |
| ---------------- | ------ | -------- | ---------- |
| 无关查询响应     | ~500ms | ~50ms    | 10倍       |
| 有效查询响应     | ~800ms | ~600ms   | 25%        |
| 实体链接失败率   | 无统计 | 快速返回 | 节省资源   |
| 低质量结果使用率 | 100%   | 智能降级 | 提升准确性 |

---

## 附录B：与现有方案的对比

| 特性       | 原方案       | GraphRAG方案（优化前） | GraphRAG方案（优化后）   |
| ---------- | ------------ | ---------------------- | ------------------------ |
| 检索方式   | 关键词搜索   | 图遍历+语义搜索        | 图遍历+语义搜索+质量评估 |
| 上下文生成 | 简单实体列表 | 结构化子图描述         | 智能分级上下文           |
| 可视化     | 基础节点展示 | 子图+路径+推理         | 子图+路径+推理+质量指标  |
| 扩展性     | 有限         | 支持多跳推理           | 支持多跳推理+智能降级    |
| 实现复杂度 | 低           | 中等                   | 中等（职责更清晰）       |
| 性能开销   | 小           | 中等（可控）           | 优化后更低               |
| 关键词提取 | 前端复杂提取 | 前端复杂提取           | **后端统一处理**         |
| 判断逻辑   | 单层复杂判断 | 单层复杂判断           | **分层快速判断**         |
| 失败处理   | 异常捕获     | 异常降级               | **质量评估+智能降级**    |

---

## 附录C：已实现功能模块详情

### C.1 后端核心模块实现

#### C.1.1 台风领域意图识别器 (TyphoonIntentRecognizer)

**文件位置**: `backend/app/services/graphrag/typhoon_intent_recognizer.py`

**功能特性**:
- 支持12种意图类型识别：基本信息查询、路径查询、强度查询、影响评估、对比分析、统计查询、预测查询、历史查询、防御措施、生成消散、相似台风、时间范围
- 支持10种实体类型抽取：台风名称、年份、地理位置、强度等级、时间范围、风速、气压、距离、月份、季节
- 基于规则+语义的多维度意图识别
- 置信度计算避免过拟合（最大0.95）

**核心配置**:
```python
# 意图类型定义
INTENT_TYPES = {
    "BASIC_INFO": "basic_info",      # 基本信息查询
    "PATH_QUERY": "path_query",      # 路径查询
    "INTENSITY_QUERY": "intensity_query",  # 强度查询
    "IMPACT_ASSESSMENT": "impact_assessment",  # 影响评估
    "COMPARISON": "comparison",      # 对比分析
    "STATISTICS": "statistics_query", # 统计查询
    "PREDICTION": "prediction",      # 预测查询
    "HISTORY": "history_query",      # 历史查询
    "DEFENSE_MEASURES": "defense_measures",  # 防御措施
    "GENESIS_DISSIPATION": "genesis_dissipation",  # 生成消散
    "SIMILAR_TYPHOONS": "similar_typhoons",  # 相似台风
    "TIME_RANGE": "time_range",      # 时间范围
}
```

#### C.1.2 动态Prompt构建器 (PromptBuilder)

**文件位置**: `backend/app/services/graphrag/prompt_builder.py`

**功能特性**:
- 11种专用Prompt模板：基本信息、路径分析、强度分析、影响评估、对比分析、统计查询、预测分析、历史查询、防御建议、生成消散、相似台风
- 动态检索指令生成
- 上下文组装与格式化
- 质量等级标记（高/中/低）

#### C.1.3 增强型检索器 (EnhancedRetriever)

**文件位置**: `backend/app/services/graphrag/enhanced_retriever.py`

**功能特性**:
- 分层检索策略：先检索depth=1节点，再检索depth=2节点
- 最大种子实体数：50个
- 最大节点数：200个
- 最大关系数：400个
- 支持多维度关联查询
- 种子实体一致性保证

**核心配置**:
```python
@dataclass
class RetrievalConfig:
    max_depth: int = 2
    max_seeds: int = 50          # 优化：从10增加到50
    max_nodes: int = 200         # 优化：从50增加到200
    max_relationships: int = 400
    min_similarity: float = 0.6
    expand_seeds: bool = True
    include_paths: bool = True
```

#### C.1.4 相关性排序器 (RelevanceRanker)

**文件位置**: `backend/app/services/graphrag/relevance_ranker.py`

**功能特性**:
- 多维度相关性评分：语义相似度、结构重要性、时效性、实体类型匹配
- 结果质量评估：节点数量、关系密度、多样性、属性完整度
- 智能排序与过滤

**评分维度**:
```python
@dataclass
class RankingWeights:
    relevance: float = 0.35      # 相关性权重
    quality: float = 0.25        # 质量权重
    diversity: float = 0.20      # 多样性权重
    freshness: float = 0.20      # 时效性权重
```

#### C.1.5 GraphRAG引擎 (GraphRAGEngine)

**文件位置**: `backend/app/services/graphrag/graphrag_engine.py`

**功能特性**:
- 统一入口：LocalSearch查询
- 意图识别与实体抽取
- 动态Prompt生成
- 分层检索执行
- 结果质量评估
- 智能降级机制

**核心方法**:
```python
async def local_search(
    self,
    query: str,
    seed_entities: Optional[List[str]] = None,
    max_depth: int = 2,
    max_nodes: int = 100,
    include_paths: bool = True
) -> LocalSearchResult:
    """执行GraphRAG本地搜索"""
```

### C.2 前端可视化组件实现

#### C.2.1 知识图谱面板 (KnowledgeGraphPanel)

**文件位置**: `frontend/src/components/KnowledgeGraphPanel.jsx`

**功能特性**:
- 三种布局模式：力导向布局、环形布局、网格布局
- 全屏模式支持
- 顶部关系类型筛选栏（12种关系类型）
- 底部节点类型筛选栏（5种节点类型）
- 节点/关系显示/隐藏控制
- 布局切换按钮组
- 种子实体高亮显示
- 遍历统计信息展示

**布局配置**:
```javascript
// 力导向布局
force: {
  repulsion: 1000,
  edgeLength: [100, 300],
  gravity: 0.1,
  layoutAnimation: false,  // 禁用扰动动画
  friction: 0.6,
}

// 网格布局
force: {
  repulsion: 500,
  edgeLength: [60, 150],
  gravity: 0.3,
  layoutAnimation: false,
  friction: 0.6,
}
```

**关系类型支持** (11种):
- HAS_PATH_POINT: 拥有路径点
- NEXT: 路径顺序
- OCCURRED_IN: 发生时间
- LANDED_AT: 登陆地点
- GENERATED_AT: 生成于
- DISSIPATED_AT: 消散于
- INTENSIFIED_TO: 增强为（包含达到强度的语义）
- WEAKENED_TO: 减弱为（包含达到强度的语义）
- SIMILAR_TO: 相似于
- AFFECTED_AREA: 影响区域
- PASSED_NEAR: 经过附近

#### C.2.2 知识图谱配置 (knowledgeGraphConfig)

**文件位置**: `frontend/src/services/knowledgeGraphConfig.js`

**功能特性**:
- 5种节点类型定义：台风、路径点、地理位置、时间、强度等级
- 11种关系类型定义
- 6种强度等级配置（TD/TS/STS/TY/STY/SuperTY）
- 节点属性字段定义
- 关系属性字段定义
- 实体验证与转换函数

### C.3 系统架构集成

#### C.3.1 后端服务集成

```
backend/app/services/graphrag/
├── __init__.py
├── graphrag_engine.py          # GraphRAG主引擎
├── typhoon_intent_recognizer.py # 意图识别器
├── prompt_builder.py           # Prompt构建器
├── enhanced_retriever.py       # 增强检索器
├── relevance_ranker.py         # 相关性排序器
└── quality_assessor.py         # 质量评估器
```

#### C.3.2 前端组件集成

```
frontend/src/components/
├── KnowledgeGraphPanel.jsx     # 知识图谱面板（优化版）
├── KnowledgeGraphVisualization.jsx  # 知识图谱可视化
└── AIAgent.jsx                 # AI客服（集成GraphRAG）

frontend/src/services/
├── knowledgeGraphConfig.js     # 知识图谱配置
└── api.js                      # API封装（含GraphRAG接口）

frontend/src/styles/
├── KnowledgeGraphPanel.css     # 知识图谱面板样式
└── KnowledgeGraphVisualization.css  # 可视化样式
```

### C.4 性能优化成果

| 优化项 | 优化前 | 优化后 | 提升 |
|--------|--------|--------|------|
| 最大种子实体数 | 10 | 50 | 5倍 |
| 最大检索节点数 | 50 | 100-200 | 2-4倍 |
| 检索深度策略 | 混合遍历 | 分层遍历 | 更完整 |
| 布局扰动 | 持续数秒 | 即时稳定 | 消除扰动 |
| 置信度计算 | 可达1.0 | 最大0.95 | 避免过拟合 |
| 种子实体一致性 | 不一致 | 严格一致 | 准确性提升 |

### C.5 API接口清单

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/kg/graphrag/search` | POST | GraphRAG本地搜索 |
| `/api/kg/graphrag/entity_linking` | POST | 实体链接 |
| `/api/kg/graphrag/multi_hop` | POST | 多跳推理 |
| `/api/kg/relationships/{typhoon_id}` | GET | 获取台风关系网络 |
| `/api/kg/search` | GET | 知识图谱搜索 |

---

_文档版本: 3.0_
_更新日期: 2026-03-02_
_更新说明: 补充已实现功能模块详情，包括意图识别器、Prompt构建器、增强检索器、相关性排序器等核心组件_
_关联文档: AIAgent知识检索功能开发方案.md, Neo4j知识图谱检索功能开发方案.md_
