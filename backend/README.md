# 台风分析系统 - 后端服务

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13+-blue.svg" alt="Python 3.13+">
  <img src="https://img.shields.io/badge/FastAPI-0.109.0-009688.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/PyTorch-2.6.0-EE4C2C.svg" alt="PyTorch">
  <img src="https://img.shields.io/badge/Qwen3--ASR-0.6B-orange.svg" alt="Qwen3-ASR">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
</p>

## 项目简介

台风分析系统后端是一个基于 **FastAPI** 构建的高性能 RESTful API 服务，专注于台风数据的智能分析、预测与可视化。系统采用异步编程模型，支持高并发访问，集成了深度学习模型进行台风路径预测，并提供 AI 智能客服、图像分析、**语音识别**等高级功能。

### 核心特性

- **高性能异步架构** - 基于 FastAPI + Uvicorn，支持高并发
- **深度学习预测** - 基于 LSTM + Attention 的台风路径预测模型
- **多 AI 模型支持** - 集成 DeepSeek、GLM、Qwen 等主流大模型
- **智能语音识别** - 集成 Qwen3-ASR 模型，支持语音转文字
- **智能图像分析** - 卫星云图自动识别与分析
- **实时数据爬取** - 自动获取中国气象局台风数据
- **完整用户系统** - JWT 认证 + OSS 头像存储

## 技术栈

### 核心框架

| 技术       | 版本    | 用途        |
| ---------- | ------- | ----------- |
| FastAPI    | 0.109.0 | Web 框架    |
| Uvicorn    | 0.27.0  | ASGI 服务器 |
| SQLAlchemy | 2.0.36  | ORM 框架    |
| Pydantic   | 2.9.2   | 数据验证    |

### AI/ML 技术

| 技术         | 版本   | 用途         |
| ------------ | ------ | ------------ |
| PyTorch      | 2.6.0  | 深度学习框架 |
| scikit-learn | 1.5.2  | 机器学习工具 |
| NumPy        | 2.1.3  | 数值计算     |
| pandas       | 2.2.3  | 数据处理     |

### AI 服务集成

- **DeepSeek** - 深度思考与推理
- **通义千问 (Qwen)** - 多模态分析
- **智谱 GLM** - 中文对话与报告生成
- **Qwen3-ASR** - 语音识别与转录

## 项目结构

```
backend/
├── app/                          # 主应用目录
│   ├── api/                      # API 路由层
│   │   ├── v1/                   # API 版本控制
│   │   ├── ai_agent.py           # AI 智能客服
│   │   ├── alert.py              # 预警管理
│   │   ├── analysis.py           # 图像分析
│   │   ├── asr.py                # 语音识别
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
│       ├── asr/                  # 语音识别服务
│       │   ├── asr_service.py    # ASR 核心服务
│       │   └── qwen_asr.py       # Qwen3-ASR 模型封装
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

### 3. 语音识别系统

集成 **Qwen3-ASR** 模型，提供高质量的语音转文字服务。

**技术特点**:

- **模型**: Qwen3-ASR-0.6B (适合 4GB 显存)
- **支持格式**: WAV, MP3, FLAC, M4A, OGG, WebM
- **语言支持**: 中文、英文、粤语等 (自动检测)
- **文本处理**: 自动繁体转简体
- **性能优化**: 启动时预加载模型，首次请求无需等待
- **GPU 加速**: 支持 CUDA 12.4，自动检测 GPU 可用性

**API 端点**:

```
POST   /api/asr/transcribe       # 语音转文字
GET    /api/asr/health           # 服务健康检查
GET    /api/asr/languages        # 支持语言列表
```

**使用示例**:

```python
import requests

# 语音识别
with open('audio.wav', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/asr/transcribe',
        files={'audio': f},
        data={'language': 'auto'}  # 可选: 'zh', 'en', 'yue'
    )
    result = response.json()
    print(result['text'])  # 识别结果
```

**响应格式**:

```json
{
  "success": true,
  "text": "现在有哪些台风？",
  "language": "zh",
  "confidence": 0.95,
  "processing_time": 1.23
}
```

### 4. 图像分析服务

卫星云图智能分析，提取台风特征。

**分析模式**:

- **基础模式** - 快速特征提取
- **高级模式** - 详细结构分析
- **OpenCV 模式** - 传统图像算法
- **融合模式** - 多方法综合

### 5. 数据爬取与同步

自动从中国气象局获取最新台风数据。

```python
# 启动定时任务
from app.services.scheduler import Scheduler

scheduler = Scheduler()
scheduler.start()
```

## 快速开始

### 环境要求

- Python >= 3.13
- CUDA >= 12.4 (GPU 加速推荐，特别是 ASR 语音识别)
- SQLite3

### 安装步骤

1. **创建虚拟环境**

```bash
cd backend
python -m venv venv312

# Windows
venv312\Scripts\activate

# Linux/Mac
source venv312/bin/activate
```

2. **安装依赖**

```bash
pip install -r requirements.txt
```

3. **安装 GPU 版 PyTorch (推荐)**

```bash
# 卸载 CPU 版本（如果已安装）
pip uninstall torch torchvision torchaudio -y

# 安装 CUDA 12.4 版本
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

4. **配置环境变量**

```bash
cp .env.example .env
# 编辑 .env 文件，配置 API 密钥
```

5. **初始化数据库**

```bash
python -c "from app.core.database import init_db; init_db()"
```

6. **导入历史数据**

```bash
python data.py
```

7. **启动服务**

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

| 分组     | 路径               | 功能       |
| -------- | ------------------ | ---------- |
| 台风数据 | `/api/typhoons`    | CRUD 操作  |
| 预测服务 | `/api/predictions` | 路径预测   |
| AI 客服  | `/api/ai`          | 智能对话   |
| 语音识别 | `/api/asr`         | 语音转文字 |
| 图像分析 | `/api/analysis`    | 云图分析   |
| 报告生成 | `/api/reports`     | 分析报告   |
| 用户认证 | `/api/auth`        | 登录注册   |

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

### ASR 语音识别配置

ASR 模块支持以下配置选项：

| 配置项       | 默认值                         | 说明           |
| ------------ | ------------------------------ | -------------- |
| 模型版本     | Qwen3-ASR-0.6B                 | 适合 4GB 显存  |
| 数据类型     | bfloat16 (GPU) / float32 (CPU) | 自动适配       |
| 最大新令牌数 | 256                            | 限制输出长度   |
| 批处理大小   | 1                              | 单文件处理     |
| 繁体转简体   | 启用                           | 自动文本规范化 |

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

### ASR 优化

- **预加载机制**: 应用启动时自动加载 ASR 模型，避免首次请求延迟
- **懒加载**: 仅在首次语音识别请求时初始化模型
- **设备自动选择**: 自动检测 CUDA 可用性，优先使用 GPU
- **内存优化**: 使用 0.6B 轻量级模型，适合消费级显卡

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
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 GPU 版 PyTorch (根据 CUDA 版本调整)
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

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

A: 检查模型文件路径和 PyTorch 版本兼容性。确保安装了正确版本的 PyTorch：
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

### Q: AI 接口调用失败？

A: 确认 API Key 配置正确且余额充足。

### Q: 数据库连接错误？

A: 检查数据库文件权限和路径配置。

### Q: ASR 语音识别返回繁体中文？

A: 系统已集成 OpenCC 自动将繁体转换为简体，无需额外配置。

### Q: ASR 首次请求响应慢？

A: 模型在启动时会自动预加载，如果仍慢请检查 GPU 是否正常工作。查看日志中的 `使用设备: cuda` 确认 GPU 已启用。

### Q: ASR 支持哪些音频格式？

A: 支持 WAV, MP3, FLAC, M4A, OGG, WebM 格式，推荐 WAV 格式以获得最佳效果。

### Q: ASR 需要多少显存？

A: 使用 Qwen3-ASR-0.6B 模型，需要约 4GB 显存。CPU 模式也可运行但速度较慢。

### Q: 安装依赖时出现编译错误？

A: 某些包（如 lxml, Pillow）在 Python 3.13 上需要较新版本。requirements.txt 已更新到兼容版本：
- lxml: 5.1.0 → 5.3.0
- Pillow: 10.0.0 → 11.0.0
- pandas: 2.1.4 → 2.2.3
- numpy: 1.26.4 → 2.1.3

### Q: FastAPI 启动时出现 Pydantic 错误？

A: 确保 pydantic 和 pydantic-settings 版本兼容：
- pydantic: 2.5.0 → 2.9.2
- pydantic-settings: 2.1.0 → 2.6.1

### Q: SQLAlchemy 出现兼容性问题？

A: Python 3.13 需要 SQLAlchemy 2.0.36+：
- sqlalchemy: 2.0.0 → 2.0.36

### Q: pkg_resources 模块找不到？

A: 需要安装特定版本的 setuptools：
```bash
pip install setuptools==69.5.1
```

## 更新日志

### v1.2.0 (2026-02-13)

- 更新依赖版本以支持 Python 3.13
- 优化 PyTorch GPU 版本安装流程
- 更新 README 安装说明

### v1.1.0 (2026-02-12)

- 新增 Qwen3-ASR 语音识别功能
- 支持语音转文字实时处理
- 自动繁体转简体文本规范化
- 模型启动预加载优化

### v1.0.0 (2026-02-08)

- 完成 FastAPI 后端架构
- 实现 LSTM 台风预测模型
- 集成多 AI 模型服务
