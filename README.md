# 🌀 台风分析系统 (Typhoon Analysis System)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/React-18-61DAFB.svg" alt="React 18">
  <img src="https://img.shields.io/badge/FastAPI-0.109.0-009688.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/阿里云-NLS-orange.svg" alt="阿里云 NLS">
  <img src="https://img.shields.io/badge/Voice%20Input-Supported-success.svg" alt="Voice Input">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
</p>

## 📋 项目简介

台风分析系统是一个基于 **FastAPI + React + AI 大模型** 的智能台风数据分析与可视化平台。系统集成了台风数据爬取、实时监控、路径可视化、统计分析、智能预测、预警管理、AI 客服、**语音识别**等功能，为气象研究和防灾减灾提供全方位的数据支持。

## ✨ 核心特性

### 🗺️ 台风路径可视化

- 基于 Leaflet 的交互式地图展示
- 支持多台风路径叠加显示
- 根据强度等级动态着色（蓝/绿/黄/橙/红/深红）
- 实时路径点详情查看（时间、位置、气压、风速）
- 年份范围：2000-2026 年
- 支持台风名称/ID 搜索

### 📊 统计分析

- 多维度数据统计（年度/月度/强度分布）
- ECharts 图表可视化（折线图、柱状图、饼图）
- 趋势分析与对比
- 数据导出（JSON/CSV 格式）
- 支持单个/批量导出

### 🤖 AI 智能客服

- 集成 DeepSeek、GLM、Qwen 等多个 AI 模型
- 支持深度思考模式（DeepSeek-R1）
- **语音输入支持** - 通过语音与 AI 交互
- 台风专业知识问答
- 对话历史记录管理
- 热门问题快速回复
- 模型自动降级和重试机制

### 🎤 语音识别 (新增)

- 集成阿里云 NLS (智能语音交互) 服务进行语音转文字
- 支持中文、英文、粤语自动检测
- 自动繁体转简体文本规范化
- 实时录音与流式识别
- 支持多种音频格式 (WAV, MP3, PCM, M4A, OGG, WebM)
- 单次录音最长 60 秒

### 🖼️ 图像分析

- 卫星云图智能分析
- 支持红外/可见光图像
- 多种分析模式（基础/高级/OpenCV/融合）
- AI 模型提取台风特征
- 图像上传和管理

### 🔮 智能预测

- 基于 LSTM 模型的路径预测
- 支持 24/48/72 小时预测
- 预测置信度评估
- 预测结果可视化
- 多机构预报路径对比

### ⚠️ 预警管理

- 多级别预警系统（蓝/黄/橙/红）
- 实时预警信息发布
- 区域预警覆盖
- 预警历史记录查询
- 自动爬取官方预警数据

### 🕷️ 自动数据爬取

- 定时爬取中国气象局数据
- 自动更新活跃台风信息
- 历史数据补充
- 失败重试机制
- 爬虫日志记录

### 📈 报告生成

- AI 自动生成台风分析报告
- 支持综合报告、预测报告、影响评估
- 多种 AI 模型可选
- 报告导出（PDF/Word）

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                     前端层 (Frontend)                    │
│  React 18 + Ant Design X + Leaflet + ECharts + Vite   │
│  端口: 5173                                             │
└─────────────────────────────────────────────────────────┘
                            ↓ HTTP/REST API
┌─────────────────────────────────────────────────────────┐
│                     后端层 (Backend)                     │
│  FastAPI + SQLAlchemy + APScheduler + httpx            │
│  端口: 8000                                             │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   数据层 (Database)                      │
│  SQLite (开发) / PostgreSQL (生产)                      │
│  表: typhoons, paths, alerts, predictions, images      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   AI 服务层 (AI Services)                │
│  DeepSeek + GLM + Qwen + 阿里云 NLS                    │
│  (通过 aiping.cn 统一接口)                             │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   数据源 (Data Source)                   │
│  中国气象局台风网 + 历史数据                             │
└─────────────────────────────────────────────────────────┘
```

## 📁 项目结构

```
TyphoonAnalysis/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/               # API路由
│   │   │   ├── typhoon.py     # 台风数据API
│   │   │   ├── statistics.py  # 统计分析API
│   │   │   ├── prediction.py  # 预测API
│   │   │   ├── export.py      # 导出API
│   │   │   ├── alert.py       # 预警API
│   │   │   ├── crawler.py     # 爬虫API
│   │   │   ├── analysis.py    # 分析API
│   │   │   ├── report.py      # 报告API
│   │   │   ├── ai_agent.py    # AI客服API
│   │   │   └── asr.py         # 语音识别API (新增)
│   │   ├── core/              # 核心配置
│   │   │   ├── config.py      # 应用配置
│   │   │   └── database.py    # 数据库配置
│   │   ├── models/            # 数据模型
│   │   │   ├── typhoon.py     # 台风相关模型
│   │   │   └── image.py       # 图像相关模型
│   │   ├── schemas/           # Pydantic模式
│   │   └── services/          # 业务逻辑
│   │       ├── ai/            # AI服务
│       ├── asr/           # 语音识别服务 (阿里云 NLS)
│   │       ├── crawler/       # 爬虫服务
│   │       ├── image/         # 图像处理
│   │       ├── lstm/          # LSTM预测
│   │       └── scheduler/     # 定时任务
│   ├── main.py                # 应用入口
│   ├── data.py                # 数据导入脚本
│   ├── requirements.txt       # Python依赖
│   ├── .env                   # 环境变量配置
│   └── README.md              # 后端文档
│
├── fronted/                    # 前端应用
│   ├── src/
│   │   ├── components/        # React组件
│   │   │   ├── MapVisualization.jsx    # 地图可视化
│   │   │   ├── StatisticsPanel.jsx     # 统计分析
│   │   │   ├── PredictionPanel.jsx     # 预测功能
│   │   │   ├── AlertPanel.jsx          # 预警管理
│   │   │   ├── AIAgent.jsx             # AI客服 (含语音输入)
│   │   │   └── ImageAnalysis.jsx       # 图像分析
│   │   ├── services/          # API服务
│   │   │   └── api.js         # API封装 (含ASR接口)
│   │   ├── styles/            # 样式文件
│   │   │   ├── AIAgent.css    # AI客服样式
│   │   │   └── ...
│   │   ├── App.jsx            # 根组件
│   │   └── main.jsx           # 入口文件
│   ├── package.json           # Node依赖
│   ├── vite.config.js         # Vite配置
│   └── README.md              # 前端文档
│
├── docs/                       # 项目文档
│   ├── 图像分析功能设计方案.md
│   └── 图像分析功能重构总结.md
│
└── README.md                   # 项目总文档（本文件）
```

## 🚀 快速开始

### 环境要求

**后端**:

- Python >= 3.10 (推荐 3.12)
- pip >= 21.0
- CUDA >= 11.7 (可选，用于 GPU 加速预测)

**前端**:

- Node.js >= 16.0
- npm >= 8.0 或 yarn >= 1.22

### 安装步骤

#### 1. 克隆项目

```bash
git clone <repository-url>
cd TyphoonAnalysis
```

#### 2. 配置后端环境

进入后端目录：

```bash
cd backend
```

**创建虚拟环境（强烈推荐）**：

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

**安装依赖**：

```bash
pip install -r requirements.txt
```

> **注意**：安装过程可能需要 5-15 分钟，取决于网络速度和硬件性能。`torch` 和 `opencv-python` 包较大，请耐心等待。

**配置环境变量**：

复制示例环境变量文件并修改：

```bash
# Windows
copy .env.example .env
# Linux/Mac
cp .env.example .env
```

编辑 `.env` 文件，配置以下关键参数：

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
DEEPSEEK_MODEL=deepseek-reasoner
DEEPSEEK_NOTHINK_MODEL=DeepSeek-R1-0528
GLM_MODEL=glm-4-plus
QWEN_TEXT_MODEL=qwen-plus
QWEN_VL_MODEL=qwen-vl-max

# 爬虫配置
CRAWLER_ENABLED=True
CRAWLER_INTERVAL_MINUTES=10
CRAWLER_START_ON_STARTUP=True

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

**重要提示**：

- 请将 `your-ai-api-key-here` 替换为您的实际 AI API 密钥
- 请将 `your-secret-key-min-32-characters-long` 替换为至少 32 位的随机字符串
- 可以从 [aiping.cn](https://aiping.cn) 获取 AI API 密钥

#### 3. 启动后端服务

确保虚拟环境已激活，然后启动服务：

```bash
python main.py
```

后端服务将在 `http://localhost:8000` 启动

> **首次启动说明**:
>
> - 确保已在 `.env` 文件中配置阿里云 NLS 参数（NLS_APPKEY, NLS_ACCESS_KEY_ID, NLS_ACCESS_KEY_SECRET）
> - 阿里云 NLS 服务需要联网使用，无需下载本地模型
> - 获取方式：登录 [阿里云智能语音交互控制台](https://nls-portal.console.aliyun.com/) 创建项目获取 AppKey

#### 4. 启动前端应用

```bash
# 打开新终端，进入前端目录
cd fronted

# 安装依赖
npm install
# 或使用 yarn
yarn install

# 启动开发服务器
npm run dev
# 或
yarn dev
```

前端应用将在 `http://localhost:5173` 启动

#### 5. 访问应用

- **前端界面**: http://localhost:5173
- **后端 API 文档**: http://localhost:8000/docs
- **ReDoc 文档**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

## 📖 使用指南

### 1. 台风路径可视化

1. 访问前端首页，点击"台风路径可视化"
2. 在左侧面板选择年份（2000-2026）
3. 可选择台风状态筛选（活跃/已停止）
4. 点击台风卡片在地图上显示路径
5. 勾选"多台风叠加显示"可同时查看多个台风
6. 鼠标悬停在路径点上查看详细信息（时间、位置、气压、风速、强度）

### 2. 统计分析

1. 点击"统计分析"进入分析面板
2. 选择统计类型（年度/月度/强度）
3. 设置年份范围
4. 点击"查询"生成图表
5. 可导出统计数据（JSON/CSV 格式）

### 3. AI 智能客服 (含语音输入)

1. 点击"AI 客服"进入对话界面
2. 选择 AI 模型（DeepSeek/GLM/Qwen）
3. 开启/关闭"深度思考"模式
   - 开启：使用 DeepSeek-R1 深度思考模型（更准确但较慢）
   - 关闭：使用常规模型（更快）
4. **语音输入**:
   - 点击输入框右侧的麦克风图标
   - 开始说话，系统实时显示录音时长
   - 再次点击或等待 60 秒自动停止
   - 语音自动转换为文字并发送
5. 查看 AI 回答和对话历史
6. 可点击热门问题快速提问

### 4. 图像分析

1. 进入"图像分析"面板
2. 上传卫星云图（支持红外/可见光图像）
3. 选择分析模式（基础/高级/OpenCV/融合）
4. 点击"开始分析"
5. 查看 AI 分析结果和提取的台风特征

### 5. 台风预测

1. 进入"台风预测"面板
2. 选择要预测的台风
3. 设置预测时长（24/48/72 小时）
4. 点击"开始预测"
5. 查看预测路径和置信度

### 6. 预警管理

1. 进入"预警管理"面板
2. 查看当前所有预警信息
3. 可按台风 ID 或预警等级筛选
4. 点击"查看详情"了解预警详情
5. 管理员可创建或删除预警

### 7. 数据导出

1. 在统计分析或台风详情页面
2. 点击"导出数据"按钮
3. 选择导出格式（JSON/CSV）
4. 勾选是否包含路径数据
5. 下载导出文件

## 🔌 API 接口

### 基础信息

- **Base URL**: `http://localhost:8000/api`
- **文档地址**: `http://localhost:8000/docs`
- **ReDoc 文档**: `http://localhost:8000/redoc`
- **认证方式**: JWT Token

### 主要端点

| 端点                       | 方法 | 说明                |
| -------------------------- | ---- | ------------------- |
| `/typhoons`                | GET  | 获取台风列表        |
| `/typhoons/{id}`           | GET  | 获取台风详情        |
| `/typhoons/{id}/path`      | GET  | 获取台风路径        |
| `/typhoons/{id}/forecast`  | GET  | 获取预报路径        |
| `/statistics/yearly`       | GET  | 获取年度统计        |
| `/statistics/intensity`    | GET  | 获取强度统计        |
| `/statistics/comparison`   | POST | 台风对比分析        |
| `/export/typhoon/{id}`     | GET  | 导出台风数据        |
| `/export/batch`            | POST | 批量导出            |
| `/prediction/path`         | POST | 预测台风路径        |
| `/prediction/intensity`    | POST | 预测台风强度        |
| `/alert/active`            | GET  | 获取活跃预警        |
| `/alert/history`           | GET  | 获取预警历史        |
| `/crawler/trigger`         | POST | 手动触发爬虫        |
| `/crawler/status`          | GET  | 获取爬虫状态        |
| `/ai-agent/sessions`       | POST | 创建 AI 对话会话    |
| `/ai-agent/sessions`       | GET  | 获取会话列表        |
| `/ai-agent/sessions/{id}`  | GET  | 获取会话历史        |
| `/ai-agent/questions`      | GET  | 获取热门问题        |
| `/ai-agent/ask`            | POST | 发送问题获取回答    |
| `/api/images/upload`       | POST | 上传图像            |
| `/api/images/analyze/{id}` | POST | 分析图像            |
| `/api/images/typhoon/{id}` | GET  | 获取台风图像列表    |
| `/report/generate`         | POST | 生成台风报告        |
| `/asr/transcribe`          | POST | 语音转文字 (新增)   |
| `/asr/health`              | GET  | ASR 健康检查 (新增) |
| `/asr/languages`           | GET  | ASR 支持语言 (新增) |

详细 API 文档请访问: http://localhost:8000/docs

## 🎨 界面预览

### 台风路径可视化

- 交互式地图展示台风路径
- 颜色编码表示强度等级
- 路径点大小反映风速

### AI 智能客服 (含语音输入)

- 多模型 AI 对话
- 语音输入按钮带脉冲动画
- 实时录音时长显示

### 统计分析面板

- 年度台风数量趋势图
- 月度分布柱状图
- 强度等级饼图

### 预警管理界面

- 预警卡片展示
- 等级颜色区分
- 详情弹窗查看

## 🛠️ 开发指南

### 后端开发

```bash
cd backend

# 安装开发依赖
pip install -r requirements.txt

# 运行测试
pytest tests/

# 代码格式化
black app/

# 类型检查
mypy app/
```

详见: [backend/README.md](backend/README.md)

### 前端开发

```bash
cd fronted

# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 预览构建
npm run preview
```

详见: [fronted/README.md](fronted/README.md)

## 📊 数据说明

### 台风强度等级

| 等级       | 风速范围      | 颜色   |
| ---------- | ------------- | ------ |
| 热带低压   | < 17.2 m/s    | 蓝色   |
| 热带风暴   | 17.2-24.4 m/s | 绿色   |
| 强热带风暴 | 24.5-32.6 m/s | 黄色   |
| 台风       | 32.7-41.4 m/s | 橙色   |
| 强台风     | 41.5-50.9 m/s | 红色   |
| 超强台风   | ≥ 51.0 m/s    | 深红色 |

### 数据来源

- **主要数据源**: 中国气象局台风网
- **更新频率**: 每小时自动爬取
- **历史数据**: 2000 年至今
- **数据准确性**: 官方权威数据

## 🐛 常见问题

### 1. 后端启动失败

**问题**: `ModuleNotFoundError: No module named 'xxx'`

**解决**:

确保已激活虚拟环境并安装所有依赖：

```bash
cd backend

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 虚拟环境相关问题

**问题**: 提示 `pip` 或 `python` 命令找不到

**解决**:

确保正确激活了虚拟环境。在 Windows PowerShell 中，如果执行策略限制，可能需要：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**问题**: 安装依赖时速度很慢

**解决**:

使用国内镜像源加速：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 环境变量配置问题

**问题**: 启动时提示缺少配置项

**解决**:

1. 确保已创建 `.env` 文件：

   ```bash
   cd backend
   copy .env.example .env  # Windows
   cp .env.example .env    # Linux/Mac
   ```

2. 编辑 `.env` 文件，填写必要的配置项（特别是 `AI_API_KEY` 和 `SECRET_KEY`）

3. 确保 `.env` 文件在 `backend` 目录下

### 4. 语音输入无法使用

**问题**: 点击麦克风无反应或识别失败

**解决**:

1. 检查浏览器是否授予麦克风权限
2. 确认后端 ASR 服务正常运行（访问 http://localhost:8000/api/asr/health 检查状态）
3. 检查 `.env` 文件中 NLS_APPKEY 等配置是否正确
4. 确认阿里云账号已开通语音识别服务
5. 生产环境需使用 HTTPS
6. 检查浏览器是否支持 Web Audio API
7. 查看后端日志获取详细错误信息

### 5. 语音识别返回繁体中文

**问题**: 识别结果显示繁体字

**解决**:

系统已集成 OpenCC 自动转换，无需手动处理。如仍有问题请检查后端日志。

### 6. 前端无法连接后端

**问题**: `Network Error` 或 `CORS Error`

**解决**:

- 确认后端服务已启动（http://localhost:8000）
- 检查防火墙设置
- 查看后端 CORS 配置
- 确认前端配置的 API 地址正确

### 7. 地图无法加载

**问题**: 地图瓦片加载失败

**解决**:

- 检查网络连接
- 当前使用高德地图瓦片（国内稳定）
- 可在代码中切换其他瓦片服务

### 8. 查询不到历史数据

**问题**: 选择历史年份无数据

**解决**:

```bash
# 确保在 backend 目录下且虚拟环境已激活
python data.py
```

### 9. 数据库锁定错误

**问题**: `database is locked`

**解决**:

- SQLite 不支持高并发
- 生产环境建议使用 PostgreSQL
- 减少并发写入操作

## 🔒 安全建议

### 开发环境

- ✅ DEBUG 模式开启
- ✅ CORS 允许所有来源
- ✅ 无需认证

### 生产环境

- ⚠️ 关闭 DEBUG 模式
- ⚠️ 配置 CORS 白名单
- ⚠️ 添加 API 认证（JWT/OAuth）
- ⚠️ 使用 HTTPS
- ⚠️ 添加限流保护
- ⚠️ 使用 PostgreSQL 替代 SQLite
- ⚠️ 配置日志监控

## 📈 性能优化

### 后端优化

- 使用异步数据库操作
- 添加数据库索引
- 实现响应缓存
- 启用 GZIP 压缩
- 使用连接池
- **ASR 流式识别**: 实时音频流处理和识别，快速响应

### 前端优化

- 组件懒加载
- 图片压缩
- 代码分割
- 使用 CDN
- 启用浏览器缓存
- **语音输入优化**: 使用 useRef 解决闭包问题

## 🔄 版本历史

### v2.1.0 (2026-02-12)

**新增功能**:

- ✅ 语音识别功能（阿里云 NLS 服务）
- ✅ AI 客服支持语音输入
- ✅ 自动繁体转简体文本规范化
- ✅ ASR 流式识别优化
- ✅ 录音计时器实时显示
- ✅ 支持多种音频格式（WAV, MP3, PCM, M4A, OGG, WebM）

**优化改进**:

- ✅ 优化语音输入按钮交互
- ✅ 修复 React 闭包导致的计时器问题
- ✅ 统一 API 调用封装
- ✅ 更新项目文档
- ✅ 使用 pydub 进行音频格式转换

### v2.0.0 (2026-01-13)

**新增功能**:

- ✅ AI 智能客服系统（支持 DeepSeek、GLM、Qwen）
- ✅ 深度思考模式（DeepSeek-R1）
- ✅ 图像分析功能（卫星云图分析）
- ✅ 多种图像分析模式（基础/高级/OpenCV/融合）
- ✅ AI 报告生成功能
- ✅ 对话历史管理
- ✅ 热门问题快速回复
- ✅ 模型自动降级和重试机制

**优化改进**:

- ✅ 统一 AI 服务接口（aiping.cn）
- ✅ 优化前后端交互逻辑
- ✅ 改进错误处理机制
- ✅ 增强日志记录
- ✅ 优化数据库查询性能

### v1.0.0 (2026-01-12)

**核心功能**:

- ✅ 台风路径可视化
- ✅ 统计分析功能
- ✅ 数据导出功能
- ✅ 预警管理系统
- ✅ 自动数据爬取
- ✅ 年份筛选（2000-2026）
- ✅ 修复 API 参数传递问题
- ✅ 优化前后端交互

### 未来计划

- 🔲 移动端适配（响应式设计）
- 🔲 实时推送通知（WebSocket）
- 🔲 用户权限管理系统
- 🔲 更多 AI 预测模型集成
- 🔲 国际化支持（多语言）
- 🔲 数据可视化增强（3D 路径）
- 🔲 台风影响范围预测
- 🔲 历史台风相似度分析
- 🔲 微信小程序版本
- 🔲 Docker 容器化部署

### 代码规范

- Python: 遵循 PEP 8
- JavaScript: 使用 4 空格缩进
- 提交信息: 使用约定式提交格式

### 数据来源

## 当前台风

- [台风快讯](http://www.nmc.cn/publish/typhoon/typhoon_new.html) -> iframe
- [SSD 当前台风](http://www.ssd.noaa.gov/PS/TROP/Basin_WestPac.html) -> iframe
- [tropicaltidbits](https://www.tropicaltidbits.com/storminfo/) -> speedDail
- [colostate](http://rammb.cira.colostate.edu/products/tc_realtime/) -> speedDail
- [WISC](http://tropic.ssec.wisc.edu/) -> speedDail
- [JMA](http://www.jma.go.jp/en/typh/) -> iframe
- [JTWC](http://www.metoc.navy.mil/jtwc/jtwc.html) -> speedDail
- [NRL(Blocked)](https://www.nrlmry.navy.mil/tc-bin/tc_home2.cgi) -> speedDail
- [数字台风网](http://agora.ex.nii.ac.jp/digital-typhoon/) -> speedDail

## 数值/路径

- [机构汇总](http://www.typhoon2000.ph/multi/log.php) -> speedDail
- [RUC 模式集合预报](https://ruc.noaa.gov/hfip/tceps/) -> speedDail
- [tropicaltidbits](https://www.tropicaltidbits.com/analysis/models/) -> speedDail
- [EMC 气旋追踪](http://www.emc.ncep.noaa.gov/gmb/tpm/emchurr/tcgen/) -> speedDail
- [12121](http://www.gd12121.com:8080/special/typhoonpattern/page/typhoonpattern.asp) -> speedDail

## 报文

[SSD 机构报文集合](http://www.ssd.noaa.gov/PS/TROP/bulletins.html) -> speedDail

[SSD 机构 ADT 分析集合](http://www.ssd.noaa.gov/PS/TROP/adt.html) -> speedDail

[WISC ADT 分析](http://tropic.ssec.wisc.edu/real-time/adt/adt.html) -> speedDail

[北京报文](http://www.nmc.cn/publish/typhoon/message.html) -> speedDail

[信息中心北京报文](http://10.148.8.228/to_pros_typonmessage.action?name=bjtfdwb) -> speedDail

[unisys 报文合集](http://www.weather.unisys.com/hurricane/archive/18040206) -> 根据系统时间动态生成链接

## 卫星

[WISC BD 色阶](http://tropic.ssec.wisc.edu/real-time/westpac/images/irbdgms5kml.GIF) -> image

[WISC NG 色阶](http://tropic.ssec.wisc.edu/real-time/westpac/images/kml/irngmskml.GIF) -> image

[SSD 西太](http://www.ssd.noaa.gov/imagery/twpac.html) -> image-TabGroup

[col-Himawari 圆盘图](http://col.st/t8E3d) -> speedDail

[col 热带](http://rammb.cira.colostate.edu/ramsdis/online/himawari-8.asp) -> speedDail

[NICT 葵花 8 即时](https://himawari8.nict.go.jp/) -> speedDail

[JMA 葵花卫星](http://www.data.jma.go.jp/mscweb/data/himawari/sat_img.php?area=se2) -> speedDail

[风云 4](http://fy4.nsmc.org.cn/nsmc/cn/image/animation.html) -> speedDail

## 相关链接

- [台湾中央气象局](https://www.cwb.gov.tw/)
- [香港天文台](http://gb.weather.gov.hk/contentc.htm)
- [澳门地球物理暨氣象局](http://www.smg.gov.mo/smg/c_index.htm)
- [菲律宾 PAGASA](https://www1.pagasa.dost.gov.ph/)
- [日本气象厅-风观测](http://www.jma.go.jp/en/amedas/000.html?elementCode=1)

- [德法强度表](http://www.ssd.noaa.gov/PS/TROP/CI-chart.html)
- [氣象常用表單位換算](http://photino.cwb.gov.tw/rdcweb/lib/comput1.htm#1)
- [计量单位换算](http://photino.cwb.gov.tw/rdcweb/lib/comput2.htm)
- [海平面气压订正](http://www.ab126.com/Geography/2204.html)

- [百度台风吧](https://tieba.baidu.com/f?kw=%E5%8F%B0%E9%A3%8E)
- [台风论坛](http://bbs.typhoon.org.cn/index.php?c=thread&fid=79)

## 🙏 致谢

- 感谢中国气象局提供台风数据
- 感谢开源社区的优秀项目
- 感谢所有贡献者的支持

---

**⚡ 快速链接**

- [前端文档](service/README.md)
- [后端文档](backend/README.md)
- [API 文档](http://localhost:8000/docs)

**🌟 如果这个项目对您有帮助，请给我们一个 Star！**
