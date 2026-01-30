# 台风分析系统 - 后端文档

## 项目简介

台风分析系统后端是一个基于 **FastAPI** 构建的高性能 RESTful API 服务，提供台风数据管理、统计分析、路径预测、AI 智能客服、图像分析等功能。采用现代化的异步编程模型，支持高并发访问。

## 技术栈

- **Web 框架**: FastAPI 0.109.0
- **ASGI 服务器**: Uvicorn 0.27.0
- **数据库**: SQLite (aiosqlite)
- **ORM**: SQLAlchemy 2.0.0 + Alembic 1.13.0
- **数据验证**: Pydantic 2.5.0
- **HTTP 客户端**: httpx 0.26.0, requests 2.31.0
- **数据处理**: pandas 2.0.0, numpy 1.24.0
- **机器学习**: torch 1.13.1, scikit-learn 1.3.0
- **图像处理**: Pillow 10.0.0
- **AI 模型**: 
  - DeepSeek (deepseek-api)
  - 通义千问 (dashscope)
  - GLM (zhipuai)
- **认证**: python-jose[cryptography] 3.3.0, passlib[bcrypt] 1.7.4
- **日志**: loguru 0.7.0
- **OSS 存储**: oss2 2.18.0, alibabacloud-oss-v2 1.2.3
- **任务调度**: APScheduler 3.10.0
- **测试**: pytest 7.4.0, pytest-asyncio 0.21.0
- **代码质量**: black 23.3.0, flake8 6.0.0

## 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 应用入口
│   ├── config.py                  # 配置管理
│   ├── database.py                # 数据库连接
│   ├── dependencies.py            # 依赖注入
│   ├── models/                    # 数据模型
│   │   ├── __init__.py
│   │   ├── typhoon.py            # 台风数据模型
│   │   ├── typhoon_path.py       # 台风路径模型
│   │   ├── alert.py              # 预警数据模型
│   │   ├── image.py              # 图像数据模型
│   │   ├── report.py             # 报告数据模型
│   │   └── user.py               # 用户数据模型
│   ├── schemas/                   # Pydantic 模式
│   │   ├── __init__.py
│   │   ├── typhoon.py            # 台风数据模式
│   │   ├── alert.py              # 预警数据模式
│   │   ├── image.py              # 图像数据模式
│   │   ├── report.py             # 报告数据模式
│   │   └── user.py               # 用户数据模式
│   ├── routers/                   # API 路由
│   │   ├── __init__.py
│   │   ├── typhoons.py           # 台风数据路由
│   │   ├── alerts.py             # 预警管理路由
│   │   ├── images.py             # 图像分析路由
│   │   ├── reports.py            # 报告生成路由
│   │   ├── predictions.py        # 预测服务路由
│   │   ├── statistics.py         # 统计分析路由
│   │   ├── auth.py               # 认证路由
│   │   └── ai.py                 # AI 客服路由
│   ├── services/                  # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── typhoon_service.py    # 台风数据服务
│   │   ├── alert_service.py      # 预警服务
│   │   ├── image_service.py      # 图像分析服务
│   │   ├── report_service.py     # 报告生成服务
│   │   ├── prediction_service.py # 预测服务
│   │   ├── statistics_service.py # 统计分析服务
│   │   ├── auth_service.py      # 认证服务
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # AI 基础服务
│   │   │   ├── deepseek_service.py  # DeepSeek 服务
│   │   │   ├── glm_service.py   # GLM 服务
│   │   │   └── qwen_service.py  # Qwen 服务
│   │   ├── lstm/
│   │   │   ├── __init__.py
│   │   │   ├── lstm_predictor.py    # LSTM 预测器
│   │   │   └── lstm_trainer.py      # LSTM 训练器
│   │   └── cv/
│   │       ├── __init__.py
│   │       └── image_processor.py  # 图像处理器
│   ├── utils/                     # 工具函数
│   │   ├── __init__.py
│   │   ├── logger.py             # 日志工具
│   │   ├── data_processor.py     # 数据处理工具
│   │   └── oss_client.py         # OSS 客户端
│   └── static/                    # 静态文件
│       └── uploads/              # 上传文件目录
├── tests/                         # 测试文件
│   ├── __init__.py
│   ├── test_api.py               # API 测试
│   ├── test_services.py          # 服务测试
│   └── test_models.py            # 模型测试
├── alembic/                       # 数据库迁移
│   ├── versions/
│   └── env.py
├── alembic.ini                    # Alembic 配置
├── data.py                        # 数据导入脚本
├── main.py                        # 应用启动入口
├── requirements.txt                # Python 依赖
├── .env.example                   # 环境变量示例
└── README.md                      # 后端文档
```

## 核心功能

### 1. 台风数据管理

**路由**: `/api/typhoons`

**功能特性**:

- 📊 台风数据 CRUD 操作
- 🔍 支持年份、状态、名称搜索
- 📥 数据导出（JSON/CSV）
- 📈 批量查询和统计
- 🗺️ 路径数据管理

**主要接口**:

```python
GET    /api/typhoons              # 获取台风列表
GET    /api/typhoons/{id}         # 获取台风详情
GET    /api/typhoons/{id}/path   # 获取台风路径
POST   /api/typhoons/search       # 搜索台风
GET    /api/typhoons/export       # 导出数据
```

### 2. 预警管理

**路由**: `/api/alerts`

**功能特性**:

- ⚠️ 预警信息管理
- 🔔 预警等级分类（蓝色/黄色/橙色/红色）
- 📝 预警详情查看
- 🗑️ 预警删除功能
- 🔍 按台风 ID 或等级筛选
- 🔄 自动刷新预警信息

**主要接口**:

```python
GET    /api/alerts/active        # 获取活跃预警
GET    /api/alerts/history        # 获取历史预警
GET    /api/alerts/{id}          # 获取预警详情
POST   /api/alerts                # 创建预警
PUT    /api/alerts/{id}          # 更新预警
DELETE /api/alerts/{id}          # 删除预警
```

### 3. 图像分析

**路由**: `/api/images`

**功能特性**:

- 🖼️ 卫星云图上传和管理
- 🔍 多种分析模式（基础/高级/OpenCV/融合）
- 🤖 AI 模型智能分析（Qwen-VL、GLM-4V）
- 📊 提取台风特征（中心位置、云系结构、强度估计）
- 📷 支持红外/可见光图像
- 📋 图像历史记录查看

**主要接口**:

```python
POST   /api/images/upload         # 上传图像
POST   /api/images/analyze        # 分析图像
GET    /api/images                # 获取图像列表
GET    /api/images/{id}          # 获取图像详情
GET    /api/images/{id}/history   # 获取分析历史
DELETE /api/images/{id}          # 删除图像
```

### 4. 报告生成

**路由**: `/api/reports`

**功能特性**:

- 📄 AI 自动生成台风分析报告
- 📊 支持综合报告、预测报告、影响评估
- 🤖 多种 AI 模型可选
- 📥 报告导出（PDF/Word）
- 📝 Markdown 格式渲染
- 🎨 支持报告预览

**报告类型**:

- **综合分析报告**：包含台风生命周期、路径特征、强度演变、历史影响
- **预测报告**：包含当前状态、未来路径预测、强度变化预测、预警建议
- **影响评估报告**：包含影响区域评估、灾害风险分析、影响程度评估、防灾减灾建议

**主要接口**:

```python
POST   /api/reports/generate      # 生成报告
GET    /api/reports/{id}          # 获取报告详情
GET    /api/reports/{id}/download  # 下载报告
GET    /api/reports               # 获取报告列表
DELETE /api/reports/{id}          # 删除报告
```

### 5. 智能预测

**路由**: `/api/predictions`

**功能特性**:

- 🤖 基于 AI 模型的路径预测
- 📍 预测未来 24/48/72 小时路径
- 🎯 显示预测置信度
- 📊 预测结果可视化
- 📈 多机构预报路径对比

**主要接口**:

```python
POST   /api/predictions/path      # 路径预测
POST   /api/predictions/intensity # 强度预测
GET    /api/predictions/{id}      # 获取预测结果
```

### 6. 统计分析

**路由**: `/api/statistics`

**功能特性**:

- 📈 台风数量统计（按年份、月份、强度）
- 📊 数据可视化支持
- 📥 统计数据导出
- 🔢 支持自定义时间范围
- ✅ 可选包含路径数据

**主要接口**:

```python
GET    /api/statistics/yearly     # 年度统计
GET    /api/statistics/monthly    # 月度统计
GET    /api/statistics/intensity  # 强度统计
POST   /api/statistics/compare    # 台风对比
```

### 7. 用户认证

**路由**: `/api/auth`

**功能特性**:

- 🔐 用户登录/注册
- 👤 头像上传（支持 OSS）
- 📝 用户信息管理
- 🔒 密码加密存储（bcrypt）
- 📧 表单验证
- 🔑 JWT 令牌认证

**主要接口**:

```python
POST   /api/auth/login            # 用户登录
POST   /api/auth/register         # 用户注册
GET    /api/auth/me               # 获取当前用户信息
PUT    /api/auth/me               # 更新用户信息
POST   /api/auth/upload-avatar    # 上传头像
```

### 8. AI 智能客服

**路由**: `/api/ai`

**功能特性**:

- 🤖 集成多个 AI 模型（DeepSeek、GLM、Qwen）
- 🧠 支持深度思考模式（DeepSeek-R1）
- 💬 实时对话交互
- 📝 对话历史记录管理
- 🔥 热门问题快速回复
- 🔄 模型自动降级和重试机制
- 📋 会话列表管理

**主要接口**:

```python
POST   /api/ai/sessions           # 创建对话会话
GET    /api/ai/sessions           # 获取会话列表
GET    /api/ai/sessions/{id}      # 获取会话历史
GET    /api/ai/questions          # 获取热门问题
POST   /api/ai/chat               # 发送问题获取回答
```

**深度思考模式说明**:

- 当开启深度思考模式时，无论选择哪个模型，都会使用 DeepSeek-R1 深度思考模型
- 深度思考模式提供更详细的推理过程和更准确的答案
- 响应时间会比常规模式长

## 数据库设计

### 数据表结构

#### 1. typhoons 表

台风基本信息表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| ty_id | String | 台风 ID |
| ty_code | String | 台风编号 |
| ty_name_ch | String | 中文名称 |
| ty_name_en | String | 英文名称 |
| ty_start_time | DateTime | 开始时间 |
| ty_end_time | DateTime | 结束时间 |
| ty_max_wind_speed | Float | 最大风速 |
| ty_min_pressure | Float | 最低气压 |
| ty_max_intensity | String | 最大强度 |
| ty_landfall | Boolean | 是否登陆 |
| ty_status | String | 状态（活跃/已消散） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### 2. typhoon_paths 表

台风路径数据表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| typhoon_id | Integer | 外键，关联 typhoons 表 |
| time | DateTime | 时间 |
| latitude | Float | 纬度 |
| longitude | Float | 经度 |
| pressure | Float | 气压 |
| wind_speed | Float | 风速 |
| intensity | String | 强度等级 |
| moving_direction | String | 移动方向 |
| moving_speed | Float | 移动速度 |
| radius_7 | Float | 7级风圈半径 |
| radius_10 | Float | 10级风圈半径 |

#### 3. alerts 表

预警信息表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| typhoon_id | Integer | 外键，关联 typhoons 表 |
| alert_level | String | 预警等级（蓝色/黄色/橙色/红色） |
| alert_time | DateTime | 预警时间 |
| alert_content | Text | 预警内容 |
| affected_area | String | 影响区域 |
| is_active | Boolean | 是否活跃 |
| created_at | DateTime | 创建时间 |

#### 4. images 表

图像数据表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| typhoon_id | Integer | 外键，关联 typhoons 表 |
| image_url | String | 图像 URL |
| image_type | String | 图像类型（红外/可见光） |
| upload_time | DateTime | 上传时间 |
| file_size | Integer | 文件大小 |
| width | Integer | 图像宽度 |
| height | Integer | 图像高度 |

#### 5. image_analyses 表

图像分析历史表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| image_id | Integer | 外键，关联 images 表 |
| analysis_mode | String | 分析模式 |
| ai_model | String | AI 模型 |
| analysis_result | Text | 分析结果（JSON） |
| extracted_features | Text | 提取的特征（JSON） |
| analysis_time | DateTime | 分析时间 |

#### 6. reports 表

报告数据表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| typhoon_id | Integer | 外键，关联 typhoons 表 |
| report_type | String | 报告类型 |
| ai_provider | String | AI 提供商 |
| report_content | Text | 报告内容（Markdown） |
| generated_at | DateTime | 生成时间 |

#### 7. users 表

用户表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| username | String | 用户名（唯一） |
| email | String | 邮箱（唯一） |
| hashed_password | String | 加密密码 |
| avatar_url | String | 头像 URL |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### 8. ai_sessions 表

AI 会话表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| session_id | String | 会话 ID（UUID） |
| user_id | Integer | 外键，关联 users 表 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### 9. ai_messages 表

AI 消息表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键 |
| session_id | String | 外键，关联 ai_sessions 表 |
| role | String | 角色（user/assistant） |
| content | Text | 消息内容 |
| model | String | AI 模型 |
| deep_thinking | Boolean | 是否深度思考 |
| created_at | DateTime | 创建时间 |

## 环境配置

### 环境变量

创建 `.env` 文件（参考 `.env.example`）：

```bash
# 应用配置
APP_NAME=TyphoonAnalysis
APP_VERSION=1.0.0
DEBUG=True

# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./typhoon.db

# JWT 配置
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI 模型配置
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com

QWEN_API_KEY=your-qwen-api-key
QWEN_BASE_URL=https://dashscope.aliyuncs.com

GLM_API_KEY=your-glm-api-key
GLM_BASE_URL=https://open.bigmodel.cn

# OSS 配置
OSS_ACCESS_KEY_ID=your-oss-access-key-id
OSS_ACCESS_KEY_SECRET=your-oss-access-key-secret
OSS_BUCKET=your-bucket-name
OSS_ENDPOINT=your-oss-endpoint
OSS_REGION=your-oss-region

# CORS 配置
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

## 安装与运行

### 环境要求

- Python >= 3.9
- pip >= 21.0

### 安装依赖

```bash
# 进入后端目录
cd backend

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 数据库初始化

```bash
# 初始化数据库
python -c "from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"

# 或使用 Alembic 迁移
alembic upgrade head
```

### 数据导入

```bash
# 导入历史台风数据（2000-2026 年）
python data.py
```

### 启动服务

```bash
# 开发模式
python main.py

# 或使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

访问 `http://localhost:8000/docs` 查看 API 文档

## API 文档

启动服务后，访问以下地址查看自动生成的 API 文档：

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 开发指南

### 代码风格

- 使用 4 空格缩进
- 遵循 PEP 8 规范
- 使用类型注解
- 编写文档字符串

### 命名规范

- 文件名: snake_case (如 `typhoon_service.py`)
- 类名: PascalCase (如 `TyphoonService`)
- 函数/变量: snake_case (如 `get_typhoon_list`)
- 常量: UPPER_SNAKE_CASE (如 `API_BASE_URL`)

### 依赖注入

FastAPI 使用依赖注入系统，定义在 `app/dependencies.py` 中：

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    # 验证 token 并返回用户
    pass
```

### 异步编程

使用 `async/await` 语法进行异步操作：

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.typhoon import Typhoon

async def get_typhoon_by_id(
    typhoon_id: int,
    db: AsyncSession
) -> Optional[Typhoon]:
    result = await db.execute(
        select(Typhoon).where(Typhoon.id == typhoon_id)
    )
    return result.scalar_one_or_none()
```

### 错误处理

使用 FastAPI 的异常处理机制：

```python
from fastapi import HTTPException, status

async def get_typhoon(typhoon_id: int):
    typhoon = await typhoon_service.get_by_id(typhoon_id)
    if not typhoon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="台风不存在"
        )
    return typhoon
```

### 日志记录

使用 loguru 记录日志：

```python
from loguru import logger

logger.info("处理请求")
logger.error("发生错误", exc_info=True)
```

## 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_api.py

# 运行特定测试函数
pytest tests/test_api.py::test_get_typhoon_list

# 查看测试覆盖率
pytest --cov=app tests/
```

### 测试示例

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_get_typhoon_list():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/typhoons")
        assert response.status_code == 200
        assert "items" in response.json()
```

## 性能优化

### 数据库优化

- 使用索引加速查询
- 批量操作减少数据库往返
- 使用连接池管理数据库连接
- 异步数据库操作

### API 优化

- 使用缓存减少重复计算
- 分页查询减少数据传输
- 异步处理提高并发性能
- 使用 CDN 加速静态资源

### 代码优化

- 使用类型注解提高代码可读性
- 遵循 SOLID 原则
- 使用依赖注入降低耦合
- 编写单元测试保证代码质量

## 部署

### Docker 部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 系统服务部署

使用 systemd 创建服务：

```ini
[Unit]
Description=Typhoon Analysis Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/backend
ExecStart=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## 常见问题

### 1. 数据库连接失败

**原因**: 数据库文件权限问题或路径错误

**解决方案**:

```bash
# 检查数据库文件权限
ls -la typhoon.db

# 修改权限
chmod 644 typhoon.db
```

### 2. AI 模型调用失败

**原因**: API Key 配置错误或额度不足

**解决方案**:

- 检查 `.env` 文件中的 API Key 配置
- 确认 API Key 有效且有足够额度
- 查看日志获取详细错误信息

### 3. OSS 上传失败

**原因**: OSS 配置错误或权限不足

**解决方案**:

- 检查 OSS 配置（AccessKey、Bucket、Endpoint）
- 确认 OSS Bucket 存在且有访问权限
- 检查网络连接

### 4. CORS 错误

**原因**: 前端域名未在 CORS 允许列表中

**解决方案**:

```python
# 在 app/main.py 中配置 CORS
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 更新日志

### v1.0.0 (2026-01-30)

**核心功能**:

- ✅ 完成 FastAPI 后端架构搭建
- ✅ 实现台风数据 CRUD 操作
- ✅ 实现预警管理功能
- ✅ 实现图像分析功能（支持多种分析模式）
- ✅ 实现报告生成功能（支持多种报告类型）
- ✅ 集成 AI 智能客服系统（DeepSeek、GLM、Qwen）
- ✅ 深度思考模式（DeepSeek-R1）
- ✅ 实现用户认证系统（JWT）
- ✅ 实现 OSS 文件上传功能
- ✅ 实现统计分析功能
- ✅ 实现台风预测功能（LSTM 模型）
- ✅ 实现数据导出功能（JSON/CSV）
- ✅ 集成日志系统（loguru）
- ✅ 实现异步数据库操作
- ✅ 完善错误处理机制

**优化改进**:

- ✅ 优化数据库查询性能
- ✅ 改进错误处理机制
- ✅ 增强代码可维护性
- ✅ 优化 API 响应速度
- ✅ 移除调试日志和 print 输出

## 技术支持

如有问题或建议，请联系开发团队或提交 Issue。

## 许可证

MIT License
