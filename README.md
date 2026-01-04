# 🌀 台风分析系统 (Typhoon Analysis System)

基于 AI 和机器学习的智能台风分析预测系统，集成了数据爬取、路径预测、强度分析、卫星云图 AI 分析等功能。

## 📋 目录

- [系统简介](#系统简介)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [API 接口文档](#api接口文档)
- [功能特性](#功能特性)
- [项目结构](#项目结构)
- [配置说明](#配置说明)
- [开发指南](#开发指南)

---

## 🎯 系统简介

台风分析系统是一个集成了多种先进技术的智能台风分析平台，主要功能包括：

- 🕷️ **数据爬取**：自动从中国气象局（CMA）爬取最新台风数据
- 🤖 **AI 分析**：基于阿里云通义千问的卫星云图智能分析
- 📊 **路径预测**：使用 LSTM 深度学习模型预测台风路径
- 💪 **强度预测**：基于机器学习的台风强度预测
- 📝 **报告生成**：自动生成专业的台风分析报告

---

## 🛠️ 技术栈

### 后端技术

- **框架**: FastAPI 0.104.1
- **数据库**: SQLite + SQLAlchemy (异步)
- **AI 服务**: 阿里云 DashScope (通义千问)
- **机器学习**: TensorFlow/Keras (LSTM 模型)
- **数据处理**: NumPy, Pandas, xarray
- **HTTP 客户端**: httpx (异步)

### 前端技术

- **框架**: 原生 HTML/CSS/JavaScript
- **UI 库**: 现代化响应式设计
- **图表**: 内置数据可视化

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.8+
- pip 包管理器
- 阿里云 DashScope API 密钥

### 2. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 配置环境变量

编辑 `backend/.env` 文件：

```env
# DashScope API配置（必需）
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./typhoon_analysis.db

# 服务器配置
DEBUG=true
HOST=0.0.0.0
PORT=8000
SECRET_KEY=your-secret-key-change-in-production-min-32-chars
```

### 4. 启动后端服务

```bash
cd backend
python main.py
```

服务将在 `http://localhost:8000` 启动

### 5. 访问前端页面

在浏览器中打开 `frontend/index.html` 文件

### 6. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 📚 API 接口文档

### 基础信息

- **Base URL**: `http://localhost:8000/api/v1`
- **Content-Type**: `application/json`
- **响应格式**: JSON

---

## 🔌 接口列表

### 1. 台风数据管理

#### 1.1 获取台风列表

**接口**: `GET /typhoons`

**描述**: 获取所有台风列表，支持分页和筛选

**请求参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| skip | int | 否 | 0 | 跳过的记录数 |
| limit | int | 否 | 100 | 返回的记录数 |
| year | int | 否 | - | 按年份筛选 |
| status | string | 否 | - | 按状态筛选 (active/inactive) |

**请求示例**:

```bash
GET /api/v1/typhoons?skip=0&limit=10&year=2024&status=active
```

**响应示例**:

```json
[
  {
    "id": 1,
    "typhoon_id": "202401",
    "typhoon_name": "AMPIL",
    "year": 2024,
    "status": "active",
    "created_at": "2024-08-01T08:00:00",
    "updated_at": "2024-08-01T08:00:00"
  }
]
```

---

#### 1.2 获取台风详情

**接口**: `GET /typhoons/{typhoon_id}`

**描述**: 获取指定台风的详细信息

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| typhoon_id | string | 是 | 台风编号 (如: 202401) |

**请求示例**:

```bash
GET /api/v1/typhoons/202401
```

**响应示例**:

```json
{
  "id": 1,
  "typhoon_id": "202401",
  "typhoon_name": "AMPIL",
  "year": 2024,
  "status": "active",
  "created_at": "2024-08-01T08:00:00",
  "updated_at": "2024-08-01T08:00:00"
}
```

---

#### 1.3 获取台风路径

**接口**: `GET /typhoons/{typhoon_id}/path`

**描述**: 获取指定台风的历史路径数据

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| typhoon_id | string | 是 | 台风编号 |

**请求示例**:

```bash
GET /api/v1/typhoons/202401/path
```

**响应示例**:

```json
[
  {
    "id": 1,
    "typhoon_id": "202401",
    "timestamp": "2024-08-01T08:00:00",
    "latitude": 25.5,
    "longitude": 125.3,
    "center_pressure": 980.0,
    "max_wind_speed": 35.0,
    "moving_speed": 15.0,
    "moving_direction": "西北",
    "intensity": "台风"
  }
]
```

---

### 2. 数据爬虫

#### 2.1 爬取活跃台风

**接口**: `POST /crawler/fetch-active-typhoons`

**描述**: 从 CMA 爬取当前所有活跃的台风信息

**请求参数**: 无

**请求示例**:

```bash
POST /api/v1/crawler/fetch-active-typhoons
Content-Type: application/json
```

**响应示例**:

```json
{
  "success": true,
  "total": 2,
  "saved": 1,
  "updated": 1
}
```

**响应字段说明**:

- `success`: 是否成功
- `total`: 爬取到的台风总数
- `saved`: 新保存的台风数量
- `updated`: 更新的台风数量

---

#### 2.2 爬取台风路径

**接口**: `POST /crawler/fetch-typhoon-path/{typhoon_id}`

**描述**: 爬取指定台风的路径数据

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| typhoon_id | string | 是 | 台风编号 (如: 202401) |

**请求示例**:

```bash
POST /api/v1/crawler/fetch-typhoon-path/202401
Content-Type: application/json
```

**响应示例**:

```json
{
  "success": true,
  "typhoon_id": "202401",
  "path_count": 48,
  "saved": 48
}
```

---

#### 2.3 获取爬虫状态

**接口**: `GET /crawler/status`

**描述**: 获取爬虫的最新状态

**请求参数**: 无

**请求示例**:

```bash
GET /api/v1/crawler/status
```

**响应示例**:

```json
{
  "status": "success",
  "task_type": "fetch_active_typhoons",
  "message": "成功爬取 2 个台风",
  "data_count": 2,
  "error_message": null,
  "created_at": "2024-08-01T08:00:00"
}
```

---

#### 2.4 获取爬虫日志

**接口**: `GET /crawler/logs`

**描述**: 获取爬虫的历史日志

**请求参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| limit | int | 否 | 50 | 返回的日志数量 (1-100) |

**请求示例**:

```bash
GET /api/v1/crawler/logs?limit=10
```

**响应示例**:

```json
[
  {
    "id": 1,
    "task_type": "fetch_active_typhoons",
    "status": "success",
    "message": "成功爬取 2 个台风",
    "data_count": 2,
    "error_message": null,
    "created_at": "2024-08-01T08:00:00"
  }
]
```

---

### 3. 智能预测

#### 3.1 路径预测

**接口**: `POST /predictions/path`

**描述**: 使用 LSTM 模型预测台风未来路径

**请求参数**:

```json
{
  "typhoon_id": "202401",
  "hours": 24,
  "model_type": "lstm"
}
```

**参数说明**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| typhoon_id | string | 是 | - | 台风编号 |
| hours | int | 否 | 24 | 预测时长（小时） |
| model_type | string | 否 | lstm | 模型类型 (lstm/arima) |

**请求示例**:

```bash
POST /api/v1/predictions/path
Content-Type: application/json

{
  "typhoon_id": "202401",
  "hours": 24,
  "model_type": "lstm"
}
```

**响应示例**:

```json
{
  "id": 1,
  "typhoon_id": "202401",
  "prediction_type": "path",
  "model_used": "lstm",
  "prediction_data": {
    "predicted_path": [
      {
        "timestamp": "2024-08-02T08:00:00",
        "latitude": 26.5,
        "longitude": 126.3
      }
    ]
  },
  "confidence_score": 0.85,
  "created_at": "2024-08-01T08:00:00"
}
```

---

#### 3.2 强度预测

**接口**: `POST /predictions/intensity`

**描述**: 预测台风未来强度变化

**请求参数**:

```json
{
  "typhoon_id": "202401",
  "hours": 24
}
```

**参数说明**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| typhoon_id | string | 是 | - | 台风编号 |
| hours | int | 否 | 24 | 预测时长（小时） |

**请求示例**:

```bash
POST /api/v1/predictions/intensity
Content-Type: application/json

{
  "typhoon_id": "202401",
  "hours": 24
}
```

**响应示例**:

```json
{
  "id": 2,
  "typhoon_id": "202401",
  "prediction_type": "intensity",
  "model_used": "random_forest",
  "prediction_data": {
    "predicted_intensity": [
      {
        "timestamp": "2024-08-02T08:00:00",
        "max_wind_speed": 40.0,
        "center_pressure": 975.0
      }
    ]
  },
  "confidence_score": 0.82,
  "created_at": "2024-08-01T08:00:00"
}
```

---

#### 3.3 获取预测历史

**接口**: `GET /predictions/{typhoon_id}`

**描述**: 获取指定台风的所有预测记录

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| typhoon_id | string | 是 | 台风编号 |

**请求示例**:

```bash
GET /api/v1/predictions/202401
```

**响应示例**:

```json
[
  {
    "id": 1,
    "typhoon_id": "202401",
    "prediction_type": "path",
    "model_used": "lstm",
    "prediction_data": {...},
    "confidence_score": 0.85,
    "created_at": "2024-08-01T08:00:00"
  }
]
```

---

### 4. AI 图像分析

#### 4.1 分析卫星云图

**接口**: `POST /ai/analyze-image`

**描述**: 使用通义千问 AI 分析台风卫星云图

**请求参数**:

```json
{
  "typhoon_id": "202401",
  "image_url": "https://example.com/typhoon.jpg",
  "analysis_type": "comprehensive"
}
```

**参数说明**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| typhoon_id | string | 是 | - | 台风编号 |
| image_url | string | 是 | - | 图像 URL 地址 |
| analysis_type | string | 否 | comprehensive | 分析类型 (comprehensive/structure/intensity) |

**请求示例**:

```bash
POST /api/v1/ai/analyze-image
Content-Type: application/json

{
  "typhoon_id": "202401",
  "image_url": "https://example.com/typhoon.jpg",
  "analysis_type": "comprehensive"
}
```

**响应示例**:

```json
{
  "id": 1,
  "typhoon_id": "202401",
  "image_url": "https://example.com/typhoon.jpg",
  "analysis_type": "comprehensive",
  "analysis_result": {
    "structure": "台风眼清晰可见，螺旋云带结构完整",
    "intensity": "强台风级别，中心气压约950hPa",
    "development_trend": "未来24小时可能继续增强"
  },
  "confidence_score": 0.88,
  "created_at": "2024-08-01T08:00:00"
}
```

---

#### 4.2 获取分析历史

**接口**: `GET /ai/analyses/{typhoon_id}`

**描述**: 获取指定台风的所有 AI 分析记录

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| typhoon_id | string | 是 | 台风编号 |

**请求示例**:

```bash
GET /api/v1/ai/analyses/202401
```

**响应示例**:

```json
[
  {
    "id": 1,
    "typhoon_id": "202401",
    "image_url": "https://example.com/typhoon.jpg",
    "analysis_type": "comprehensive",
    "analysis_result": {...},
    "confidence_score": 0.88,
    "created_at": "2024-08-01T08:00:00"
  }
]
```

---

### 5. 报告生成

#### 5.1 生成台风报告

**接口**: `POST /reports/generate`

**描述**: 生成台风分析报告

**请求参数**:

```json
{
  "typhoon_id": "202401",
  "report_type": "comprehensive",
  "include_prediction": true,
  "include_ai_analysis": true
}
```

**参数说明**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| typhoon_id | string | 是 | - | 台风编号 |
| report_type | string | 否 | comprehensive | 报告类型 (comprehensive/path/intensity) |
| include_prediction | bool | 否 | true | 是否包含预测信息 |
| include_ai_analysis | bool | 否 | true | 是否包含 AI 分析 |

**请求示例**:

```bash
POST /api/v1/reports/generate
Content-Type: application/json

{
  "typhoon_id": "202401",
  "report_type": "comprehensive",
  "include_prediction": true,
  "include_ai_analysis": true
}
```

**响应示例**:

```json
{
  "id": 1,
  "typhoon_id": "202401",
  "report_type": "comprehensive",
  "report_content": "# 台风AMPIL分析报告\n\n## 基本信息\n...",
  "generated_at": "2024-08-01T08:00:00"
}
```

---

#### 5.2 获取报告列表

**接口**: `GET /reports`

**描述**: 获取所有报告列表

**请求参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| skip | int | 否 | 0 | 跳过的记录数 |
| limit | int | 否 | 100 | 返回的记录数 |
| typhoon_id | string | 否 | - | 按台风 ID 筛选 |

**请求示例**:

```bash
GET /api/v1/reports?skip=0&limit=10&typhoon_id=202401
```

**响应示例**:

```json
[
  {
    "id": 1,
    "typhoon_id": "202401",
    "report_type": "comprehensive",
    "report_content": "...",
    "generated_at": "2024-08-01T08:00:00"
  }
]
```

---

#### 5.3 获取报告详情

**接口**: `GET /reports/{report_id}`

**描述**: 获取指定报告的详细内容

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| report_id | int | 是 | 报告 ID |

**请求示例**:

```bash
GET /api/v1/reports/1
```

**响应示例**:

```json
{
  "id": 1,
  "typhoon_id": "202401",
  "report_type": "comprehensive",
  "report_content": "# 台风AMPIL分析报告\n\n## 基本信息\n...",
  "generated_at": "2024-08-01T08:00:00"
}
```

---

## 🎨 功能特性

### 1. 数据爬取

- ✅ 自动爬取 CMA 台风数据
- ✅ 支持多个 API 源自动切换
- ✅ 智能数据解析和格式转换
- ✅ 完整的日志记录和错误处理

### 2. 智能预测

- ✅ LSTM 深度学习路径预测
- ✅ 随机森林强度预测
- ✅ 多模型集成预测
- ✅ 置信度评估

### 3. AI 分析

- ✅ 卫星云图智能分析
- ✅ 台风结构识别
- ✅ 强度评估
- ✅ 发展趋势预测

### 4. 报告生成

- ✅ 自动生成专业报告
- ✅ 支持多种报告类型
- ✅ Markdown 格式输出
- ✅ 集成预测和 AI 分析结果

---

## 📁 项目结构

```
TyphoonAnalysis/
├── backend/                          # 后端服务
│   ├── app/                         # 应用代码
│   │   ├── api/                     # API路由
│   │   │   └── v1/                 # API v1版本
│   │   │       ├── typhoons.py     # 台风数据API
│   │   │       ├── crawler.py      # 爬虫API
│   │   │       ├── predictions.py  # 预测API
│   │   │       ├── ai.py           # AI分析API
│   │   │       └── reports.py      # 报告API
│   │   ├── core/                   # 核心配置
│   │   │   ├── config.py          # 配置管理
│   │   │   └── database.py        # 数据库连接
│   │   ├── models/                 # 数据模型
│   │   │   └── typhoon.py         # 台风相关模型
│   │   ├── schemas/                # 数据模式
│   │   │   ├── typhoon.py         # 台风数据模式
│   │   │   ├── prediction.py      # 预测数据模式
│   │   │   └── report.py          # 报告数据模式
│   │   ├── services/               # 业务逻辑
│   │   │   ├── crawler/           # 爬虫服务
│   │   │   │   └── cma_crawler.py # CMA爬虫
│   │   │   ├── ml/                # 机器学习
│   │   │   │   ├── lstm_predictor.py    # LSTM预测器
│   │   │   │   └── intensity_predictor.py # 强度预测器
│   │   │   └── ai/                # AI服务
│   │   │       └── qwen_service.py # 通义千问服务
│   │   └── utils/                  # 工具函数
│   ├── data/                       # 数据目录
│   │   ├── 202408.2407/           # 台风数据
│   │   ├── images/                # 图像文件
│   │   └── models/                # 训练模型
│   ├── logs/                       # 日志目录
│   ├── scripts/                    # 脚本工具
│   ├── main.py                     # 入口文件
│   ├── requirements.txt            # 依赖列表
│   ├── .env                        # 环境配置
│   └── typhoon_analysis.db         # SQLite数据库
├── frontend/                        # 前端页面
│   └── index.html                  # 功能测试平台
├── PROJECT_DOCUMENTATION.md        # 完整项目文档
└── README.md                       # 项目说明（本文件）
```

---

## ⚙️ 配置说明

### 环境变量配置

编辑 `backend/.env` 文件进行配置：

```env
# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./typhoon_analysis.db

# DashScope API配置（必需）
# 请在 https://dashscope.console.aliyun.com/ 获取您的API密钥
DASHSCOPE_API_KEY=sk-your-api-key-here

# AI模型配置
QWEN_PLUS_MODEL=qwen-plus          # 文本分析模型
QWEN_VL_MODEL=qwen-vl-max          # 视觉分析模型
AI_TIMEOUT=30                       # AI请求超时时间（秒）

# 服务器配置
DEBUG=true                          # 调试模式
HOST=0.0.0.0                       # 监听地址
PORT=8000                          # 监听端口
SECRET_KEY=your-secret-key-change-in-production-min-32-chars

# CORS配置
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost:8080"]

# CMA爬虫配置
# 注意：CMA网站的API地址可能会变化，如遇到404错误请更新以下地址
CMA_BASE_URL=https://typhoon.slt.zj.gov.cn
CMA_TYPHOON_LIST_URL=https://typhoon.slt.zj.gov.cn/Api/TyphoonActivity
CRAWLER_INTERVAL=3600              # 爬取间隔（秒）
CRAWLER_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# 日志配置
LOG_LEVEL=INFO                     # 日志级别 (DEBUG/INFO/WARNING/ERROR)
LOG_FILE=logs/app.log              # 日志文件路径

# 数据存储路径
DATA_DIR=./data                    # 数据目录
IMAGES_DIR=./data/images           # 图像目录
MODELS_DIR=./data/models           # 模型目录
```

### 配置项说明

| 配置项            | 说明                      | 必填 | 默认值                                    |
| ----------------- | ------------------------- | ---- | ----------------------------------------- |
| DATABASE_URL      | 数据库连接 URL            | 是   | sqlite+aiosqlite:///./typhoon_analysis.db |
| DASHSCOPE_API_KEY | 阿里云 DashScope API 密钥 | 是   | -                                         |
| QWEN_PLUS_MODEL   | 通义千问文本模型          | 否   | qwen-plus                                 |
| QWEN_VL_MODEL     | 通义千问视觉模型          | 否   | qwen-vl-max                               |
| AI_TIMEOUT        | AI 请求超时时间           | 否   | 30                                        |
| DEBUG             | 调试模式                  | 否   | false                                     |
| HOST              | 服务监听地址              | 否   | 0.0.0.0                                   |
| PORT              | 服务监听端口              | 否   | 8000                                      |
| SECRET_KEY        | 应用密钥（至少 32 位）    | 是   | -                                         |
| CORS_ORIGINS      | 允许的跨域源              | 否   | []                                        |
| CMA_BASE_URL      | CMA 台风网基础 URL        | 否   | https://typhoon.slt.zj.gov.cn             |
| CRAWLER_INTERVAL  | 爬虫间隔时间（秒）        | 否   | 3600                                      |
| LOG_LEVEL         | 日志级别                  | 否   | INFO                                      |
| DATA_DIR          | 数据存储目录              | 否   | ./data                                    |

---

## 👨‍💻 开发指南

### 本地开发

1. **克隆项目**

```bash
git clone <repository-url>
cd TyphoonAnalysis
```

2. **创建虚拟环境**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **配置环境变量**

```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置
```

5. **初始化数据库**

```bash
python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
```

6. **启动开发服务器**

```bash
python main.py
```

### 代码规范

- **Python**: 遵循 PEP 8 规范
- **缩进**: 4 个空格
- **命名**:
  - 类名: PascalCase
  - 函数/变量: snake_case
  - 常量: UPPER_SNAKE_CASE
- **类型注解**: 使用类型提示
- **文档字符串**: 使用中文注释

### 测试

```bash
# 运行单元测试
pytest tests/

# 运行测试并生成覆盖率报告
pytest --cov=app tests/
```

### API 测试

使用内置的 Swagger UI 进行 API 测试：

1. 启动后端服务
2. 访问 http://localhost:8000/docs
3. 在 Swagger UI 中测试各个接口

---

## 🔧 常见问题

### 1. 爬虫无法获取数据

**问题**: 爬虫返回空列表或 404 错误

**解决方案**:

- 检查网络连接
- 确认 CMA API 地址是否可访问
- 更新 `.env` 文件中的 `CMA_BASE_URL` 和 `CMA_TYPHOON_LIST_URL`
- 查看爬虫日志了解详细错误信息

### 2. AI 分析失败

**问题**: AI 分析返回错误或超时

**解决方案**:

- 确认 `DASHSCOPE_API_KEY` 配置正确
- 检查 API 密钥是否有效且有足够的额度
- 增加 `AI_TIMEOUT` 配置值
- 确认图像 URL 可访问

### 3. 预测模型未找到

**问题**: 路径预测返回"模型未找到"错误

**解决方案**:

- 确认 `backend/data/models/` 目录存在
- 使用训练脚本训练模型
- 检查模型文件路径配置

### 4. 数据库连接错误

**问题**: 启动时数据库连接失败

**解决方案**:

- 确认 `DATABASE_URL` 配置正确
- 检查数据库文件权限
- 删除旧的数据库文件重新初始化

### 5. CORS 跨域错误

**问题**: 前端请求被 CORS 策略阻止

**解决方案**:

- 在 `.env` 文件中添加前端地址到 `CORS_ORIGINS`
- 重启后端服务

---

## 📊 数据说明

### 台风数据格式

系统使用的台风数据包含以下字段：

| 字段             | 类型     | 说明                   |
| ---------------- | -------- | ---------------------- |
| typhoon_id       | string   | 台风编号（如：202401） |
| typhoon_name     | string   | 台风名称（如：AMPIL）  |
| year             | int      | 年份                   |
| timestamp        | datetime | 观测时间               |
| latitude         | float    | 纬度（度）             |
| longitude        | float    | 经度（度）             |
| center_pressure  | float    | 中心气压（hPa）        |
| max_wind_speed   | float    | 最大风速（m/s）        |
| wind_radius_7    | float    | 7 级风圈半径（km）     |
| moving_speed     | float    | 移动速度（km/h）       |
| moving_direction | string   | 移动方向               |
| intensity        | string   | 强度等级               |

### NC 文件说明

`backend/data/` 目录中的 NC 文件是 NetCDF 格式的卫星数据文件，包含：

- 卫星观测数据
- 气象要素场
- 时间序列信息

这些文件可用于：

- 训练 LSTM 预测模型
- 分析台风演变过程
- 生成可视化图表

---

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 📞 联系方式

- 项目地址: [GitHub Repository]
- 问题反馈: [Issues]
- 邮箱: your-email@example.com

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
- [阿里云 DashScope](https://dashscope.aliyun.com/) - AI 服务支持
- [TensorFlow](https://www.tensorflow.org/) - 机器学习框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL 工具包

---

## 📝 更新日志

### v2.0.0 (2024-12-30)

- ✅ 完整的 API 接口文档
- ✅ 修复爬虫功能，支持多 API 源
- ✅ 优化数据存储结构
- ✅ 改进错误处理和日志记录
- ✅ 更新前端界面

### v1.0.0 (2024-08-01)

- 🎉 初始版本发布
- ✅ 基础台风数据管理
- ✅ LSTM 路径预测
- ✅ AI 图像分析
- ✅ 报告生成功能

---

**🌀 台风分析系统 - 让台风预测更智能！**
