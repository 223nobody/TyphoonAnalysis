# 台风分析系统 - 后端服务

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/FastAPI-0.109.0-009688.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/PyTorch-1.13.1-EE4C2C.svg" alt="PyTorch">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
</p>

## 项目简介

台风分析系统后端是一个基于 **FastAPI** 构建的高性能 RESTful API 服务，专注于台风数据的智能分析、预测与可视化。系统采用异步编程模型，支持高并发访问，集成了深度学习模型进行台风路径预测，并提供 AI 智能客服、图像分析等高级功能。

### 核心特性

- **高性能异步架构** - 基于 FastAPI + Uvicorn，支持高并发
- **深度学习预测** - 基于 LSTM + Attention 的台风路径预测模型
- **多 AI 模型支持** - 集成 DeepSeek、GLM、Qwen 等主流大模型
- **智能图像分析** - 卫星云图自动识别与分析
- **实时数据爬取** - 自动获取中国气象局台风数据
- **完整用户系统** - JWT 认证 + OSS 头像存储

## 技术栈

### 核心框架

| 技术       | 版本    | 用途        |
| ---------- | ------- | ----------- |
| FastAPI    | 0.109.0 | Web 框架    |
| Uvicorn    | 0.27.0  | ASGI 服务器 |
| SQLAlchemy | 2.0.0   | ORM 框架    |
| Pydantic   | 2.5.0   | 数据验证    |

### AI/ML 技术

| 技术         | 版本   | 用途         |
| ------------ | ------ | ------------ |
| PyTorch      | 1.13.1 | 深度学习框架 |
| scikit-learn | 1.3.0  | 机器学习工具 |
| NumPy        | 1.24.0 | 数值计算     |
| pandas       | 2.0.0  | 数据处理     |

### AI 服务集成

- **DeepSeek** - 深度思考与推理
- **通义千问 (Qwen)** - 多模态分析
- **智谱 GLM** - 中文对话与报告生成

## 项目结构

```
backend/
├── app/                          # 主应用目录
│   ├── api/                      # API 路由层
│   │   ├── v1/                   # API 版本控制
│   │   ├── ai_agent.py           # AI 智能客服
│   │   ├── alert.py              # 预警管理
│   │   ├── analysis.py           # 图像分析
│   │   ├── auth.py               # 用户认证
│   │   ├── crawler.py            # 数据爬取
│   │   ├── export.py             # 数据导出
│   │   ├── prediction.py         # 台风预测
│   │   ├── report.py             # 报告生成
│   │   ├── statistics.py         # 统计分析
│   │   ├── typhoon.py            # 台风数据
│   │   └── user_stats.py         # 用户统计
│   ├── core/                     # 核心配置
│   │   ├── auth.py               # 认证逻辑
│   │   ├── config.py             # 全局配置
│   │   └── database.py           # 数据库连接
│   ├── models/                   # 数据模型
│   │   ├── typhoon.py            # 台风模型
│   │   ├── user.py               # 用户模型
│   │   └── image.py              # 图像模型
│   ├── schemas/                  # Pydantic 模式
│   └── services/                 # 业务服务层
│       ├── ai/                   # AI 服务
│       │   ├── deepseek_service.py
│       │   ├── glm_service.py
│       │   └── qwen_service.py
│       ├── crawler/              # 数据爬取
│       │   ├── cma_crawler.py    # 中国气象局
│       │   └── bulletin_crawler.py
│       ├── image/                # 图像分析
│       ├── lstm/                 # LSTM 预测
│       ├── prediction/           # 预测服务
│       │   ├── data/             # 数据处理
│       │   ├── models/           # 模型定义
│       │   ├── utils/            # 工具函数
│       │   ├── predictor.py      # 基础预测器
│       │   ├── predictor_advanced.py  # 高级预测
│       │   └── predictor_fallback.py  # 降级预测
│       └── scheduler/            # 定时任务
├── data/                         # 数据目录
│   └── csv/                      # CSV 数据集
├── models/                       # 预训练模型
├── training/                     # 模型训练脚本
│   ├── train_model.py            # 基础训练
│   ├── train_model_enhanced.py   # 增强训练
│   ├── evaluate_model.py         # 模型评估
│   ├── select_best_model.py      # 模型选择
│   └── test_best_model.py        # 模型测试
├── main.py                       # 应用入口
├── data.py                       # 数据导入
└── requirements.txt              # 依赖列表
```

## 核心功能模块

### 1. 台风预测系统

基于 LSTM + Attention 的深度学习模型，支持未来 24/48/72 小时路径预测。

```python
from app.services.prediction import TyphoonPredictor

# 初始化预测器
predictor = TyphoonPredictor(model_path='./models/best_model.pth')

# 执行预测
result = await predictor.predict_from_csv(
    typhoon_id='202001',
    forecast_hours=48
)
```

**预测特性**:

- 支持任意起点预测
- 滚动预测模式
- 置信度评估
- 自动降级机制

### 2. AI 智能客服

集成多模型 AI 对话系统，支持深度思考模式。

**API 端点**:

```
POST   /api/ai/chat              # 对话交互
GET    /api/ai/sessions          # 会话管理
GET    /api/ai/questions         # 热门问题
```

**模型支持**:
| 模型 | 特点 | 适用场景 |
|------|------|----------|
| DeepSeek-R1 | 深度思考 | 复杂推理 |
| DeepSeek-V3 | 通用对话 | 日常问答 |
| GLM-4 | 中文优化 | 报告生成 |
| Qwen-VL | 多模态 | 图像分析 |

### 3. 图像分析服务

卫星云图智能分析，提取台风特征。

**分析模式**:

- **基础模式** - 快速特征提取
- **高级模式** - 详细结构分析
- **OpenCV 模式** - 传统图像算法
- **融合模式** - 多方法综合

### 4. 数据爬取与同步

自动从中国气象局获取最新台风数据。

```python
# 启动定时任务
from app.services.scheduler import Scheduler

scheduler = Scheduler()
scheduler.start()
```

## 快速开始

### 环境要求

- Python >= 3.9
- CUDA >= 11.7 (GPU 训练可选)
- SQLite3

### 安装步骤

1. **创建虚拟环境**

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

2. **安装依赖**

```bash
pip install -r requirements.txt
```

3. **配置环境变量**

```bash
cp .env.example .env
# 编辑 .env 文件，配置 API 密钥
```

4. **初始化数据库**

```bash
python -c "from app.core.database import init_db; init_db()"
```

5. **导入历史数据**

```bash
python data.py
```

6. **启动服务**

```bash
# 开发模式
python main.py

# 生产模式
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

访问 `http://localhost:8000/docs` 查看 API 文档。

## 模型训练

### 训练新模型

```bash
# 基础训练
cd training
python train_model.py --epochs 50 --batch-size 32

# 增强训练（推荐）
python train_model_enhanced.py --epochs 100 --early-stopping 15
```

### 评估与选择

```bash
# 评估模型
python evaluate_model.py --model-path ../models/best_model.pth

# 选择最佳模型
python select_best_model.py --models-dir ../models

# 测试模型
python test_best_model.py
```

### 训练参数

| 参数                 | 默认值 | 说明         |
| -------------------- | ------ | ------------ |
| `--epochs`           | 50/100 | 训练轮数     |
| `--batch-size`       | 32/64  | 批次大小     |
| `--lr`               | 0.001  | 学习率       |
| `--sequence-length`  | 12     | 输入序列长度 |
| `--prediction-steps` | 8      | 预测步数     |
| `--early-stopping`   | 15     | 早停耐心值   |

## API 文档

启动服务后访问：

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

### 主要 API 分组

| 分组     | 路径               | 功能      |
| -------- | ------------------ | --------- |
| 台风数据 | `/api/typhoons`    | CRUD 操作 |
| 预测服务 | `/api/predictions` | 路径预测  |
| AI 客服  | `/api/ai`          | 智能对话  |
| 图像分析 | `/api/analysis`    | 云图分析  |
| 报告生成 | `/api/reports`     | 分析报告  |
| 用户认证 | `/api/auth`        | 登录注册  |

## 配置说明

### 环境变量 (.env)

```bash
# 应用配置
APP_NAME=TyphoonAnalysis
DEBUG=False

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./typhoon.db

# JWT 密钥
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI API 密钥
DEEPSEEK_API_KEY=your-key
QWEN_API_KEY=your-key
GLM_API_KEY=your-key

# OSS 配置
OSS_ACCESS_KEY_ID=your-key
OSS_ACCESS_KEY_SECRET=your-secret
OSS_BUCKET=your-bucket
OSS_ENDPOINT=your-endpoint
```

## 性能优化

### 数据库优化

- 索引加速查询
- 异步连接池
- 批量操作

### API 优化

- 响应缓存
- 分页查询
- 异步处理

### 模型优化

- 模型量化
- 批处理预测
- GPU 加速

## 测试

```bash
# 运行测试
pytest

# 覆盖率报告
pytest --cov=app --cov-report=html

# 特定测试
pytest tests/test_prediction.py -v
```

## 部署

### Docker 部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 生产环境建议

1. 使用 Gunicorn + Uvicorn Worker
2. 配置 Nginx 反向代理
3. 启用 HTTPS
4. 配置日志轮转
5. 设置监控告警

## 常见问题

### Q: 模型加载失败？

A: 检查模型文件路径和 PyTorch 版本兼容性。

### Q: AI 接口调用失败？

A: 确认 API Key 配置正确且余额充足。

### Q: 数据库连接错误？

A: 检查数据库文件权限和路径配置。

## 更新日志

### v1.0.0 (2026-02-08)

- 完成 FastAPI 后端架构
- 实现 LSTM 台风预测模型
- 集成多 AI 模型服务
- 添加图像分析功能
- 完善用户认证系统

## 许可证

MIT License © 2026 TyphoonAnalysis Team

报告数据表

| 字段名         | 类型     | 说明                   |
| -------------- | -------- | ---------------------- |
| id             | Integer  | 主键                   |
| typhoon_id     | Integer  | 外键，关联 typhoons 表 |
| report_type    | String   | 报告类型               |
| ai_provider    | String   | AI 提供商              |
| report_content | Text     | 报告内容（Markdown）   |
| generated_at   | DateTime | 生成时间               |

#### 7. users 表

用户表

| 字段名          | 类型     | 说明           |
| --------------- | -------- | -------------- |
| id              | Integer  | 主键           |
| username        | String   | 用户名（唯一） |
| email           | String   | 邮箱（唯一）   |
| hashed_password | String   | 加密密码       |
| avatar_url      | String   | 头像 URL       |
| created_at      | DateTime | 创建时间       |
| updated_at      | DateTime | 更新时间       |

#### 8. ai_sessions 表

AI 会话表

| 字段名     | 类型     | 说明                |
| ---------- | -------- | ------------------- |
| id         | Integer  | 主键                |
| session_id | String   | 会话 ID（UUID）     |
| user_id    | Integer  | 外键，关联 users 表 |
| created_at | DateTime | 创建时间            |
| updated_at | DateTime | 更新时间            |

#### 9. ai_messages 表

AI 消息表

| 字段名        | 类型     | 说明                      |
| ------------- | -------- | ------------------------- |
| id            | Integer  | 主键                      |
| session_id    | String   | 外键，关联 ai_sessions 表 |
| role          | String   | 角色（user/assistant）    |
| content       | Text     | 消息内容                  |
| model         | String   | AI 模型                   |
| deep_thinking | Boolean  | 是否深度思考              |
| created_at    | DateTime | 创建时间                  |

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