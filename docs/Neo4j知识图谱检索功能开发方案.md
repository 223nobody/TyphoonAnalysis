# 台风分析系统 - Neo4j知识图谱检索功能开发方案

## 目录

1. [需求分析与功能定义](#一需求分析与功能定义)
2. [Neo4j数据库模型设计](#二neo4j数据库模型设计)
3. [数据导入策略](#三数据导入策略)
4. [检索算法实现](#四检索算法实现)
5. [API接口开发](#五api接口开发)
6. [前端交互设计](#六前端交互设计)
7. [性能优化方案](#七性能优化方案)
8. [部署流程](#八部署流程)

---

## 一、需求分析与功能定义

### 1.1 现有系统架构

| 层级   | 技术栈                         | 说明                          |
| ------ | ------------------------------ | ----------------------------- |
| 前端   | React 18 + Vite + Ant Design 6 | 台风可视化、预测分析          |
| 后端   | FastAPI + Neo4j                | RESTful API服务               |
| AI服务 | DeepSeek/Qwen/GLM              | 多模型AI分析                  |
| 数据   | CSV + Neo4j                    | 1966-2026年台风路径和登陆数据 |

### 1.2 CSV数据源

#### 路径数据 (`typhoon_paths_1966_2026.csv`)

| 字段             | 说明           | 示例                |
| ---------------- | -------------- | ------------------- |
| ty_code          | 台风编号       | 196601              |
| ty_name_en       | 英文名称       | HESTER              |
| ty_name_ch       | 中文名称       | 海斯特              |
| timestamp        | 时间戳         | 1966-04-04 00:00:00 |
| latitude         | 纬度           | 7.3                 |
| longitude        | 经度           | 165.8               |
| center_pressure  | 中心气压(hPa)  | 1000                |
| max_wind_speed   | 最大风速(m/s)  | 10.0                |
| moving_speed     | 移动速度(km/h) | 15                  |
| moving_direction | 移动方向       | NW                  |
| intensity        | 强度等级       | 热带低压            |
| power            | 风力等级       | 5                   |

#### 登陆数据 (`typhoon_land_1966_2026.csv`)

| 字段         | 说明     | 示例                                 |
| ------------ | -------- | ------------------------------------ |
| ty_code      | 台风编号 | 201002                               |
| ty_name_en   | 英文名称 | CONSON                               |
| ty_name_ch   | 中文名称 | 康森                                 |
| land_address | 登陆地点 | 三亚                                 |
| land_time    | 登陆时间 | 2010-07-16 19:50:00                  |
| land_lng     | 登陆经度 | 109.5                                |
| land_lat     | 登陆纬度 | 18.09                                |
| land_info    | 登陆描述 | 台风"康森"16日19时50分在海南三亚登陆 |
| land_strong  | 登陆强度 | 台风                                 |

### 1.3 知识图谱功能

| 功能模块     | 具体功能                   | 优先级 |
| ------------ | -------------------------- | ------ |
| **智能检索** | 自然语言查询台风信息       | P0     |
| **关联分析** | 台风相似性分析、路径关联   | P0     |
| **历史比对** | 相似台风历史案例推荐       | P1     |
| **影响评估** | 基于历史数据的灾害影响预测 | P1     |

---

## 二、Neo4j数据库模型设计

### 2.1 节点类型 (5种)

```
┌─────────────────────────────────────────────────────────────┐
│                      节点类型 (Labels)                       │
├─────────────────────────────────────────────────────────────┤
│  (:Typhoon)        - 台风节点                               │
│  (:PathPoint)      - 路径点节点                             │
│  (:Location)       - 地理位置节点（登陆地点）                │
│  (:Time)           - 时间节点（年份）                        │
│  (:Intensity)      - 强度等级节点（静态定义）                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 关系类型

```
┌─────────────────────────────────────────────────────────────┐
│                     关系类型 (Relationships)                 │
├─────────────────────────────────────────────────────────────┤
│  基础关系                                                    │
│  (:Typhoon)-[:LANDED_AT]->(:Location)       登陆地点        │
│  (:Typhoon)-[:OCCURRED_IN]->(:Time)         发生时间        │
│  (:Typhoon)-[:REACHED_INTENSITY]->(:Intensity) 达到强度     │
│  (:Typhoon)-[:HAS_PATH_POINT]->(:PathPoint) 路径点         │
│  (:PathPoint)-[:NEXT]->(:PathPoint)          路径顺序        │
├─────────────────────────────────────────────────────────────┤
│  扩展关系 - 台风生命周期                                     │
│  (:Typhoon)-[:GENERATED_AT]->(:Location)    生成位置        │
│  (:Typhoon)-[:DISSIPATED_AT]->(:Location)   消散位置        │
├─────────────────────────────────────────────────────────────┤
│  扩展关系 - 强度变化                                         │
│  (:Typhoon)-[:INTENSIFIED_TO]->(:Intensity) 强度增强        │
│  (:Typhoon)-[:WEAKENED_TO]->(:Intensity)    强度减弱        │
├─────────────────────────────────────────────────────────────┤
│  扩展关系 - 相似性                                           │
│  (:Typhoon)-[:SIMILAR_TO]->(:Typhoon)       相似台风        │
├─────────────────────────────────────────────────────────────┤
│  扩展关系 - 地理影响                                         │
│  (:Typhoon)-[:AFFECTED_AREA]->(:Location)   影响区域        │
│  (:Typhoon)-[:PASSED_NEAR]->(:Location)     经过附近        │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 节点属性定义

#### 台风节点 (:Typhoon)

| 属性              | 类型    | 说明                                     |
| ----------------- | ------- | ---------------------------------------- |
| typhoon_id        | string  | 台风编号（唯一标识，格式YYYYMM）         |
| name_cn           | string  | 中文名称（来自CSV: ty_name_ch）          |
| name_en           | string  | 英文名称（来自CSV: ty_name_en）          |
| year              | integer | 年份（来自CSV: ty_code前4位）            |
| max_wind_speed    | float   | 最大风速 m/s（路径点最大值）             |
| min_pressure      | float   | 最低气压 hPa（路径点最小值）             |
| max_power         | integer | 最高风力等级（0-17级）                   |
| peak_intensity    | string  | 峰值强度等级（TD/TS/STS/TY/STY/SuperTY） |
| total_path_points | integer | 路径点总数                               |
| duration_hours    | integer | 持续时长（小时）                         |
| start_lat         | float   | 起始纬度（第一个路径点）                 |
| start_lon         | float   | 起始经度                                 |
| end_lat           | float   | 结束纬度（最后一个路径点）               |
| end_lon           | float   | 结束经度                                 |
| avg_moving_speed  | float   | 平均移动速度 km/h                        |
| max_moving_speed  | float   | 最大移动速度 km/h                        |
| total_distance_km | float   | 总移动距离（计算得出）                   |
| landfall_count    | integer | 登陆次数                                 |
| start_time        | integer | 生成时间戳（毫秒）                       |
| end_time          | integer | 消散时间戳（毫秒）                       |

#### 路径点节点 (:PathPoint)

| 属性             | 类型    | 说明                            |
| ---------------- | ------- | ------------------------------- |
| typhoon_id       | string  | 台风编号                        |
| sequence         | integer | 序列号（按时间排序）            |
| lat              | float   | 纬度                            |
| lon              | float   | 经度                            |
| timestamp        | integer | 观测时间戳（毫秒）              |
| hour_of_year     | integer | 年内小时数                      |
| pressure         | float   | 中心气压 hPa                    |
| wind_speed       | float   | 最大风速 m/s                    |
| intensity        | string  | 强度等级中文名                  |
| intensity_level  | string  | 强度等级代码                    |
| power            | integer | 风力等级（0-17级）              |
| moving_direction | string  | 移动方向（N/NE/E/SE/S/SW/W/NW） |
| moving_speed     | float   | 移动速度 km/h                   |
| distance_to_next | float   | 到下一个路径点距离 km           |

#### 地理位置节点 (:Location)

| 属性        | 类型   | 说明         |
| ----------- | ------ | ------------ |
| name        | string | 地点名称     |
| lat         | float  | 纬度         |
| lon         | float  | 经度         |
| intensity   | string | 登陆时强度   |
| description | string | 登陆描述信息 |

#### 时间节点 (:Time)

| 属性                      | 类型    | 说明             |
| ------------------------- | ------- | ---------------- |
| year                      | integer | 年份             |
| total_typhoons            | integer | 该年台风总数     |
| total_landfalls           | integer | 该年登陆次数     |
| strongest_typhoon_id      | string  | 最强台风编号     |
| strongest_wind_speed      | float   | 最强台风最大风速 |
| strongest_intensity_level | string  | 最强台风等级     |

#### 强度节点 (:Intensity)

**注意**：强度节点是**静态定义**的，只有6个（TD, TS, STS, TY, STY, SuperTY），所有台风共享。

| 属性           | 类型   | 说明         |
| -------------- | ------ | ------------ |
| level          | string | 等级代码     |
| name_cn        | string | 中文名称     |
| wind_speed_min | float  | 最小风速 m/s |
| wind_speed_max | float  | 最大风速 m/s |

**时间信息说明**：由于一个台风在生命周期中可能经历多个强度等级，时间信息存储在 `REACHED_INTENSITY` **关系**上，而不是节点上。

#### REACHED_INTENSITY 关系属性

| 属性           | 类型     | 说明                     |
| -------------- | -------- | ------------------------ |
| start_time     | datetime | 达到该强度的开始时间     |
| end_time       | datetime | 维持该强度的结束时间     |
| duration_hours | float    | 维持该强度的时长（小时） |
| point_count    | integer  | 该强度下的路径点数量     |
| max_wind_speed | float    | 该强度期间的最大风速     |

#### LANDED_AT 关系属性

| 属性      | 类型     | 说明       |
| --------- | -------- | ---------- |
| land_time | datetime | 登陆时间   |
| lat       | float    | 登陆纬度   |
| lon       | float    | 登陆经度   |
| intensity | string   | 登陆时强度 |

#### GENERATED_AT / DISSIPATED_AT 关系属性（生命周期）

| 属性        | 类型     | 说明   |
| ----------- | -------- | ------ |
| timestamp   | datetime | 时间戳 |
| lat         | float    | 纬度   |
| lon         | float    | 经度   |
| description | string   | 描述   |

#### INTENSIFIED_TO / WEAKENED_TO 关系属性（强度变化）

| 属性              | 类型     | 说明         |
| ----------------- | -------- | ------------ |
| from_level        | string   | 原强度等级   |
| to_level          | string   | 目标强度等级 |
| change_time       | datetime | 变化时间     |
| wind_speed_change | float    | 风速变化     |
| pressure_change   | float    | 气压变化     |

#### SIMILAR_TO 关系属性（相似性）

| 属性                 | 类型     | 说明            |
| -------------------- | -------- | --------------- |
| similarity_score     | float    | 综合相似度(0-1) |
| path_similarity      | float    | 路径形状相似度  |
| genesis_similarity   | float    | 生成位置相似度  |
| intensity_similarity | float    | 强度变化相似度  |
| temporal_similarity  | float    | 时间模式相似度  |
| calculated_at        | datetime | 计算时间        |

#### AFFECTED_AREA / PASSED_NEAR 关系属性（地理影响）

| 属性            | 类型     | 说明                      |
| --------------- | -------- | ------------------------- |
| min_distance_km | float    | 最小距离(公里)            |
| passed_at       | datetime | 经过时间                  |
| impact_level    | string   | 影响级别(low/medium/high) |

---

## 三、数据导入策略

### 3.1 项目结构

```
backend/
├── app/
│   ├── core/
│   │   ├── neo4j_client.py      # Neo4j连接管理
│   │   └── config.py            # 配置
│   ├── models/
│   │   └── knowledge_graph.py   # 数据模型定义
│   ├── services/
│   │   └── knowledge_graph/
│   │       ├── query_engine.py  # 查询引擎
│   │       └── similarity.py    # 相似性计算
│   └── api/
│       └── knowledge_graph.py   # API路由
├── scripts/
│   ├── init_neo4j_schema.py     # 初始化Schema
│   ├── import_full_data.py      # 全量导入脚本
│   ├── clear_db.py              # 清空数据库
│   └── verify_import.py         # 数据验证
└── data/
    └── csv/
        ├── typhoon_paths_1966_2026.csv
        └── typhoon_land_1966_2026.csv
```

### 3.2 导入流程

```bash
# 1. 清空数据库
python backend/scripts/clear_db.py

# 2. 执行全量导入
python backend/scripts/import_full_data.py

# 3. 验证导入结果
python backend/scripts/verify_import.py
```

### 3.3 实际导入结果

| 实体/关系类型     | 实际数量 | 说明                |
| ----------------- | -------- | ------------------- |
| (:Typhoon)        | 1,398个  | 1966-2026年所有台风 |
| (:PathPoint)      | 58,523个 | 所有路径观测点      |
| (:Location)       | 225个    | 去重后的登陆地点    |
| (:Time)           | 82个     | 有台风的年份        |
| (:Intensity)      | 6个      | 静态定义的强度等级  |
| [:LANDED_AT]      | 261个    | 台风-登陆地点关系   |
| [:HAS_PATH_POINT] | 58,523个 | 台风-路径点关系     |
| [:NEXT]           | 57,125个 | 路径点顺序关系      |
| [:OCCURRED_IN]    | 1,398个  | 台风-年份关系       |
| [:HAS_INTENSITY]  | 1,398个  | 台风-强度关系       |

---

## 四、检索算法实现

### 4.1 查询引擎

核心功能：

- **精确查询**：按台风编号、名称查询
- **模糊查询**：按名称关键词搜索
- **相似性查询**：基于DTW算法计算路径相似度
- **时序查询**：按年份、时间段筛选

### 4.2 相似性计算

使用DTW（动态时间规整）算法计算台风路径相似度：

```python
# 核心思路
1. 提取两条台风路径的经纬度序列
2. 计算DTW距离
3. 转换为相似度分数（0-1）
4. 返回最相似的台风列表
```

---

## 五、API接口开发

### 5.1 主要接口

| 接口                           | 方法 | 说明             |
| ------------------------------ | ---- | ---------------- |
| `/api/kg/search`               | POST | 智能搜索         |
| `/api/kg/similar`              | POST | 查找相似台风     |
| `/api/kg/typhoon/{id}`         | GET  | 获取台风详情     |
| `/api/kg/typhoon/{id}/path`    | GET  | 获取台风路径     |
| `/api/kg/typhoon/{id}/network` | GET  | 获取关联网络     |
| `/api/kg/statistics/yearly`    | GET  | 年度统计         |
| `/api/kg/node-types`           | GET  | 获取节点类型配置 |

### 5.2 请求示例

```bash
# 搜索台风
curl -X POST http://localhost:8000/api/kg/search \
  -H "Content-Type: application/json" \
  -d '{"query": "海斯特", "limit": 10}'

# 查找相似台风
curl -X POST http://localhost:8000/api/kg/similar \
  -H "Content-Type: application/json" \
  -d '{"typhoon_id": "196601", "limit": 5}'
```

---

## 六、前端交互设计

### 6.1 主要组件

| 组件                        | 说明           |
| --------------------------- | -------------- |
| KnowledgeGraphVisualization | 知识图谱主页面 |
| KnowledgeGraphCanvas        | 图谱可视化画布 |
| KnowledgeGraphFilter        | 筛选面板       |

### 6.2 节点配置

节点类型配置在 `frontend/src/services/knowledgeGraphConfig.js` 中定义，包含：

- 节点类型标识
- 显示名称和颜色
- 字段定义（名称、类型、显示标签）

---

## 七、性能优化方案

| 优化策略     | 具体措施                              | 效果             |
| ------------ | ------------------------------------- | ---------------- |
| **索引优化** | 为typhoon_id、year、timestamp创建索引 | 查询速度提升50%+ |
| **批量导入** | 使用UNWIND进行批量插入                | 导入速度提升10x  |
| **查询限制** | 默认限制返回50条，最大深度3层         | 避免查询爆炸     |
| **连接池**   | 连接池大小50                          | 并发性能优化     |

---

## 八、部署流程

### 8.1 环境配置

```python
# backend/app/core/config.py
NEO4J_URI: str = "bolt://localhost:7687"
NEO4J_USER: str = "neo4j"
NEO4J_PASSWORD: str = "your_password"
```

### 8.2 启动步骤

```bash
# 1. 启动Neo4j
docker-compose up -d neo4j

# 2. 导入数据
python backend/scripts/import_full_data.py

# 3. 启动后端
python backend/main.py

# 4. 启动前端
cd frontend && npm run dev
```

### 8.3 访问地址

- 前端: http://localhost:5173
- 后端API: http://localhost:8000
- Neo4j Browser: http://localhost:7474

---

_文档版本: 3.0_  
_最后更新: 2026-02-28_  
_更新说明: 根据实际实现优化，修正节点类型数量，更新字段定义和导入结果_
