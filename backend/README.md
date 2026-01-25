# 台风分析系统 - 后端文档

## 📋 项目简介

台风分析系统后端是基于 **FastAPI** 构建的高性能异步 API 服务，提供台风数据管理、统计分析、路径预测、数据爬取、AI 智能客服、图像分析等核心功能。采用异步数据库操作，支持定时任务调度，集成多个 AI 大模型。

## 🚀 技术栈

- **Web 框架**: FastAPI 0.104+
- **数据库**: SQLite + SQLAlchemy 2.0 (异步)
- **数据爬取**: httpx + BeautifulSoup4
- **定时任务**: APScheduler
- **日志**: Loguru
- **数据处理**: Pandas + NumPy
- **HTTP 客户端**: httpx (异步)
- **AI 服务**: DeepSeek + GLM + Qwen (通过 aiping.cn)
- **图像处理**: OpenCV + Pillow
- **机器学习**: TensorFlow/Keras (LSTM 预测)

## 📁 项目结构

```
backend/
├── app/
│   ├── api/                    # API 路由模块
│   │   ├── typhoon.py         # 台风数据 API
│   │   ├── statistics.py      # 统计分析 API
│   │   ├── prediction.py      # 预测功能 API
│   │   ├── export.py          # 数据导出 API
│   │   ├── alert.py           # 预警管理 API
│   │   ├── crawler.py         # 爬虫控制 API
│   │   ├── analysis.py        # 数据分析 API
│   │   ├── report.py          # 报告生成 API
│   │   ├── ai_agent.py        # AI 客服 API
│   │   └── v1/
│   │       └── images.py      # 图像分析 API
│   ├── core/                   # 核心配置
│   │   ├── config.py          # 应用配置（环境变量）
│   │   └── database.py        # 数据库配置（异步引擎）
│   ├── models/                 # 数据模型
│   │   ├── typhoon.py         # 台风数据模型
│   │   ├── alert.py           # 预警模型
│   │   ├── prediction.py      # 预测模型
│   │   └── image.py           # 图像模型
│   ├── schemas/                # Pydantic 模式
│   │   ├── typhoon.py         # 台风数据模式
│   │   ├── alert.py           # 预警模式
│   │   └── statistics.py      # 统计模式
│   └── services/               # 业务逻辑层
│       ├── ai/                # AI 服务
│       │   ├── ai_service.py  # AI 统一服务接口
│       │   └── models.py      # AI 模型配置
│       ├── crawler/           # 爬虫服务
│       │   ├── bulletin_crawler.py  # 公报爬虫
│       │   └── typhoon_crawler.py   # 台风数据爬虫
│       ├── image/             # 图像处理
│       │   ├── analyzer.py    # 图像分析器
│       │   └── processor.py   # 图像预处理
│       ├── lstm/              # LSTM 预测
│       │   └── predictor.py   # 路径预测器
│       └── scheduler.py       # 定时任务调度
├── main.py                     # 应用入口
├── data.py                     # 数据导入脚本
├── requirements.txt            # Python 依赖
├── .env                        # 环境变量配置
├── typhoon_analysis.db         # SQLite 数据库
└── README.md                   # 本文档
```

## 🛠️ 安装与运行

### 环境要求

- Python >= 3.10
- pip >= 21.0

### 安装依赖

```bash
# 进入后端目录
cd backend

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 环境变量配置

在 `backend` 目录下创建 `.env` 文件：

```env
# 应用配置
APP_NAME=台风分析系统
APP_VERSION=2.0.0
DEBUG=True
SECRET_KEY=your-secret-key-min-32-characters-long

# 服务器配置
HOST=0.0.0.0
PORT=8000

# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./typhoon_analysis.db

# AI 服务配置（统一使用 aiping.cn 接口）
AI_API_KEY=your-ai-api-key-here
AI_API_BASE_URL=https://aiping.cn/api/v1

# AI 模型配置
DEEPSEEK_MODEL=deepseek-reasoner              # 深度思考模型
DEEPSEEK_NOTHINK_MODEL=DeepSeek-R1-0528       # 非深度思考模型
GLM_MODEL=glm-4-plus                          # GLM 模型
QWEN_TEXT_MODEL=qwen-plus                     # Qwen 文本模型
QWEN_VL_MODEL=qwen-vl-max                     # Qwen 视觉模型

# 爬虫配置
CRAWLER_ENABLED=True
CRAWLER_INTERVAL_MINUTES=10
CRAWLER_START_ON_STARTUP=True

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

**配置说明**：

| 配置项                     | 说明                    | 默认值            |
| -------------------------- | ----------------------- | ----------------- |
| `AI_API_KEY`               | AI API 密钥（必须配置） | 无                |
| `SECRET_KEY`               | 应用密钥（至少 32 位）  | 无                |
| `DEEPSEEK_MODEL`           | DeepSeek 深度思考模型   | deepseek-reasoner |
| `DEEPSEEK_NOTHINK_MODEL`   | DeepSeek 非深度思考模型 | DeepSeek-R1-0528  |
| `GLM_MODEL`                | GLM 模型                | glm-4-plus        |
| `QWEN_TEXT_MODEL`          | Qwen 文本模型           | qwen-plus         |
| `QWEN_VL_MODEL`            | Qwen 视觉模型           | qwen-vl-max       |
| `CRAWLER_ENABLED`          | 是否启用爬虫            | True              |
| `CRAWLER_INTERVAL_MINUTES` | 爬虫执行间隔（分钟）    | 10                |

**重要提示**：

- 请将 `your-ai-api-key-here` 替换为您的实际 AI API 密钥
- 请将 `your-secret-key-min-32-characters-long` 替换为至少 32 位的随机字符串
- 可以从 [aiping.cn](https://aiping.cn) 获取 AI API 密钥

### 数据库初始化

```bash
# 首次运行会自动创建数据库表
python main.py
```

### 启动服务

```bash
# 开发模式（自动重载）
python main.py

# 或使用uvicorn直接启动
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后访问：

- API 文档: `http://localhost:8000/docs`
- ReDoc 文档: `http://localhost:8000/redoc`
- 健康检查: `http://localhost:8000/health`

## 🗄️ 数据库设计

### 台风基础信息表 (typhoons)

| 字段            | 类型        | 说明                     |
| --------------- | ----------- | ------------------------ |
| id              | Integer     | 主键（自增）             |
| typhoon_id      | String(50)  | 台风编号（唯一）         |
| typhoon_name    | String(100) | 英文名称                 |
| typhoon_name_cn | String(100) | 中文名称                 |
| year            | Integer     | 年份                     |
| status          | Integer     | 状态（0=已停止, 1=活跃） |
| max_wind_speed  | Float       | 最大风速(m/s)            |
| min_pressure    | Float       | 最低气压(hPa)            |
| start_time      | DateTime    | 开始时间                 |
| end_time        | DateTime    | 结束时间                 |
| created_at      | DateTime    | 创建时间                 |
| updated_at      | DateTime    | 更新时间                 |

### 台风路径表 (typhoon_paths)

| 字段           | 类型       | 说明             |
| -------------- | ---------- | ---------------- |
| id             | Integer    | 主键（自增）     |
| typhoon_id     | String(50) | 台风编号（外键） |
| timestamp      | DateTime   | 观测时间         |
| latitude       | Float      | 纬度             |
| longitude      | Float      | 经度             |
| pressure       | Float      | 中心气压(hPa)    |
| wind_speed     | Float      | 最大风速(m/s)    |
| move_speed     | Float      | 移动速度(km/h)   |
| move_direction | String(10) | 移动方向         |
| intensity      | String(50) | 强度等级         |
| created_at     | DateTime   | 创建时间         |

### 预警信息表 (alerts)

| 字段        | 类型        | 说明         |
| ----------- | ----------- | ------------ |
| id          | Integer     | 主键（自增） |
| typhoon_id  | String(50)  | 台风编号     |
| alert_level | String(20)  | 预警等级     |
| alert_type  | String(50)  | 预警类型     |
| region      | String(100) | 预警区域     |
| description | Text        | 预警描述     |
| issue_time  | DateTime    | 发布时间     |
| expire_time | DateTime    | 过期时间     |
| created_at  | DateTime    | 创建时间     |

## 🔌 API 接口文档

### 1. 台风数据管理

#### 获取台风列表

```http
GET /api/typhoons?year={year}&status={status}&limit={limit}
```

**参数**:

- `year` (可选): 年份筛选
- `status` (可选): 状态筛选（0=已停止, 1=活跃）
- `limit` (可选): 返回数量（默认 50，最大 100）

**响应**:

```json
{
  "total": 100,
  "items": [
    {
      "typhoon_id": "202501",
      "typhoon_name": "KONG-REY",
      "typhoon_name_cn": "康妮",
      "year": 2025,
      "status": 1,
      "max_wind_speed": 45.0,
      "min_pressure": 960.0
    }
  ]
}
```

#### 获取台风详情

```http
GET /api/typhoons/{typhoon_id}
```

#### 获取台风路径

```http
GET /api/typhoons/{typhoon_id}/path
```

**响应**:

```json
{
  "total": 50,
  "items": [
    {
      "timestamp": "2025-01-01T00:00:00",
      "latitude": 15.5,
      "longitude": 125.3,
      "pressure": 980.0,
      "wind_speed": 35.0,
      "intensity": "台风"
    }
  ]
}
```

### 2. 统计分析

#### 获取统计数据

```http
GET /api/statistics?start_year={year}&end_year={year}&group_by={type}
```

**参数**:

- `start_year`: 起始年份
- `end_year`: 结束年份
- `group_by`: 分组方式（year/month/intensity）

**响应**:

```json
{
  "group_by": "year",
  "data": [
    { "label": "2020", "count": 23 },
    { "label": "2021", "count": 22 }
  ]
}
```

### 3. 数据导出

#### 导出单个台风数据

```http
GET /api/export/typhoon/{typhoon_id}?format={format}&include_path={bool}
```

**参数**:

- `format`: 导出格式（json/csv）
- `include_path`: 是否包含路径数据

#### 批量导出

```http
POST /api/export/batch
Content-Type: application/json

{
    "year": 2025,
    "format": "json",
    "include_path": true
}
```

### 4. 台风预测

#### 预测台风路径

```http
POST /api/predictions/predict
Content-Type: application/json

{
    "typhoon_id": "202501",
    "hours": 24
}
```

**响应**:

```json
{
  "typhoon_id": "202501",
  "predictions": [
    {
      "timestamp": "2025-01-02T00:00:00",
      "latitude": 16.0,
      "longitude": 126.0,
      "confidence": 0.85
    }
  ]
}
```

### 5. 预警管理

#### 获取预警列表

```http
GET /api/alerts?typhoon_id={id}&alert_level={level}
```

#### 创建预警

```http
POST /api/alerts
Content-Type: application/json

{
    "typhoon_id": "202501",
    "alert_level": "orange",
    "alert_type": "typhoon_warning",
    "region": "福建沿海",
    "description": "预计24小时内影响",
    "issue_time": "2025-01-01T12:00:00",
    "expire_time": "2025-01-02T12:00:00"
}
```

### 6. 数据爬取

#### 手动触发爬虫

```http
POST /api/crawler/trigger
```

#### 获取爬虫状态

```http
GET /api/crawler/status
```

### 7. AI 智能客服

#### 创建对话会话

```http
POST /api/ai-agent/sessions
Content-Type: application/json

{
    "title": "台风咨询"
}
```

**响应**:

```json
{
  "session_id": "uuid-string",
  "title": "台风咨询",
  "created_at": "2025-01-01T12:00:00"
}
```

#### 发送问题获取回答

```http
POST /api/ai-agent/ask
Content-Type: application/json

{
    "session_id": "uuid-string",
    "question": "台风的形成条件是什么？",
    "model": "deepseek",
    "deep_thinking": false
}
```

**参数说明**:

- `session_id`: 会话 ID
- `question`: 用户问题
- `model`: AI 模型（deepseek/glm/qwen）
- `deep_thinking`: 是否启用深度思考模式（仅对 DeepSeek 有效）

**响应**:

```json
{
  "answer": "台风的形成需要以下条件：1. 海水温度...",
  "model": "deepseek",
  "timestamp": "2025-01-01T12:00:00"
}
```

#### 获取会话历史

```http
GET /api/ai-agent/sessions/{session_id}
```

#### 获取热门问题

```http
GET /api/ai-agent/questions
```

### 8. 图像分析

#### 上传图像

```http
POST /api/images/upload
Content-Type: multipart/form-data

{
    "file": <binary>,
    "typhoon_id": "202501",
    "image_type": "infrared",
    "description": "红外卫星云图"
}
```

**响应**:

```json
{
  "image_id": "uuid-string",
  "filename": "typhoon_202501.jpg",
  "upload_time": "2025-01-01T12:00:00"
}
```

#### 分析图像

```http
POST /api/images/analyze/{image_id}
Content-Type: application/json

{
    "analysis_mode": "advanced",
    "model": "qwen-vl"
}
```

**参数说明**:

- `analysis_mode`: 分析模式（basic/advanced/opencv/fusion）
- `model`: AI 模型（qwen-vl/glm-4v）

**响应**:

```json
{
  "analysis_result": "图像显示台风中心位于...",
  "features": {
    "center_location": [15.5, 125.3],
    "cloud_pattern": "螺旋状",
    "intensity_estimate": "强台风"
  },
  "analysis_time": "2025-01-01T12:00:00"
}
```

#### 获取台风图像列表

```http
GET /api/images/typhoon/{typhoon_id}
```

## ⚙️ 配置说明

### 环境变量配置

创建 `.env` 文件（可选）：

```env
# 应用配置
APP_NAME=台风分析系统
APP_VERSION=1.0.0
DEBUG=True

# 服务器配置
HOST=0.0.0.0
PORT=8000

# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./typhoon_analysis.db

# 日志配置
LOG_LEVEL=INFO

# 爬虫配置
CRAWLER_INTERVAL=3600  # 爬取间隔（秒）
```

### 配置文件

**文件**: `app/core/config.py`

```python
class Settings(BaseSettings):
    APP_NAME: str = "台风分析系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DATABASE_URL: str = "sqlite+aiosqlite:///./typhoon_analysis.db"
    LOG_LEVEL: str = "INFO"
```

## 🕷️ 数据爬取

### 爬虫服务

**文件**: `app/services/crawler.py`

**数据源**: 中国气象局台风网

**爬取内容**:

- 台风基础信息
- 实时路径数据
- 强度变化信息

**定时任务**:

- 默认每小时执行一次
- 自动更新活跃台风数据
- 失败自动重试

### 手动导入数据

```bash
# 运行数据导入脚本
python data.py
```

## 📊 定时任务

### 任务调度器

**文件**: `app/services/scheduler.py`

**已配置任务**:

1. **台风数据爬取**: 每小时执行
2. **数据清理**: 每天凌晨执行
3. **预警检查**: 每 30 分钟执行

### 添加自定义任务

```python
from app.services.scheduler import scheduler

@scheduler.scheduled_job('interval', hours=1)
async def my_task():
    # 任务逻辑
    pass
```

## 🐛 常见问题

### 1. 数据库锁定错误

**错误**: `database is locked`

**原因**: SQLite 不支持高并发写入

**解决方案**:

- 使用异步操作
- 减少并发写入
- 生产环境建议使用 PostgreSQL/MySQL

### 2. 爬虫失败

**错误**: `Connection timeout`

**原因**: 网络问题或目标网站限制

**解决方案**:

- 检查网络连接
- 增加超时时间
- 添加请求头和 User-Agent

### 3. 内存占用过高

**原因**: 大量数据加载到内存

**解决方案**:

- 使用分页查询
- 限制单次返回数量
- 使用流式处理

## 🔒 安全建议

### 生产环境配置

1. **关闭 DEBUG 模式**

```python
DEBUG = False
```

2. **配置 CORS 白名单**

```python
allow_origins=["https://yourdomain.com"]
```

3. **添加 API 认证**

```python
from fastapi.security import HTTPBearer
```

4. **使用 HTTPS**

```bash
uvicorn main:app --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

5. **限流保护**

```python
from slowapi import Limiter
```

## 📝 开发规范

### 代码风格

- 使用 4 空格缩进
- 遵循 PEP 8 规范
- 使用类型注解
- 编写文档字符串

### 异步编程规范

```python
# ✅ 正确：使用异步函数
async def get_typhoon(db: AsyncSession, typhoon_id: str):
    result = await db.execute(query)
    return result.scalar_one_or_none()

# ❌ 错误：在异步函数中使用同步操作
async def get_typhoon(db: AsyncSession, typhoon_id: str):
    return db.query(Typhoon).filter(...).first()  # 错误！
```

### API 设计规范

- 使用 RESTful 风格
- 返回统一的响应格式
- 提供详细的错误信息
- 使用 HTTP 状态码

## 🧪 测试

### 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-asyncio httpx

# 运行测试
pytest tests/
```

### API 测试示例

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_typhoons():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/typhoons")
        assert response.status_code == 200
```

## 📈 性能优化

### 数据库优化

1. **添加索引**

```python
Index('idx_typhoon_year', 'year')
Index('idx_typhoon_status', 'status')
```

2. **使用连接池**

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10
)
```

3. **批量操作**

```python
db.add_all(objects)
await db.commit()
```

### API 优化

1. **响应压缩**

```python
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware)
```

2. **缓存机制**

```python
from fastapi_cache import FastAPICache
```

## 🔄 更新日志

### v1.0.0 (2026-01-12)

- ✅ 完成核心 API 接口
- ✅ 实现数据爬取功能
- ✅ 添加定时任务调度
- ✅ 支持数据导出
- ✅ 实现预警管理
- ✅ 优化数据库查询性能

## 📞 技术支持

如有问题或建议，请联系开发团队或提交 Issue。

## 📄 许可证

MIT License
