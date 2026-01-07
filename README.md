# 台风路径可视化系统 (Typhoon Analysis System)

## 📋 项目简介

台风路径可视化系统是一个基于 Web 的台风数据分析和可视化平台，集成了台风路径追踪、数据查询、智能预测、图像分析和 AI 报告生成等功能。

### 主要功能

- 🗺️ **台风路径可视化** - 基于 Leaflet.js 的交互式地图展示台风路径
- 🔍 **台风数据查询** - 支持按年份、状态等条件筛选台风数据
- 🤖 **智能预测** - 基于历史数据的台风路径预测
- 📸 **图像分析** - 卫星云图智能分析（支持 URL 和本地文件上传）
- 📊 **AI 报告生成** - 集成通义千问和 DeepSeek 的智能报告生成

---

## 🛠️ 技术栈

### 后端

- **框架**: FastAPI (Python 3.8+)
- **数据库**: SQLite
- **AI 集成**: 通义千问 (Qwen)、DeepSeek
- **异步处理**: asyncio, httpx

### 前端

- **核心**: HTML5, CSS3, JavaScript (ES6+)
- **地图库**: Leaflet.js 1.9.4
- **地图服务**: 高德地图 (中文标注)
- **UI 设计**: 响应式布局，渐变色主题

---

## 📁 项目结构

```
TyphoonAnalysis/
├── backend/                    # 后端代码
│   ├── app/                   # 应用模块
│   │   ├── __init__.py
│   │   ├── api/              # API路由
│   │   │   ├── typhoon.py    # 台风数据API
│   │   │   ├── prediction.py # 预测API
│   │   │   ├── analysis.py   # 图像分析API
│   │   │   ├── report.py     # 报告生成API
│   │   │   └── crawler.py    # 爬虫API
│   │   ├── models/           # 数据模型
│   │   ├── services/         # 业务逻辑
│   │   └── utils/            # 工具函数
│   ├── main.py               # FastAPI应用入口
│   ├── data.py               # 数据初始化
│   ├── requirements.txt      # Python依赖
│   └── typhoon_analysis.db   # SQLite数据库
├── frontend/                  # 前端代码
│   └── index.html            # 单页应用
├── .vscode/                  # VSCode配置
│   └── settings.json         # Live Server配置
├── .gitignore               # Git忽略文件
└── README.md                # 项目文档
```

---

## 🚀 安装和运行

### 环境要求

- Python 3.8 或更高版本
- pip (Python 包管理器)
- 现代浏览器 (Chrome, Firefox, Edge)
- VSCode + Live Server 扩展 (推荐)

### 1. 克隆项目

```bash
git clone <repository-url>
cd TyphoonAnalysis
```

### 2. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 配置环境变量

在 `backend` 目录下创建 `.env` 文件：

```env
# AI服务配置
QWEN_API_KEY=your_qwen_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 数据库配置
DATABASE_URL=sqlite:///./typhoon_analysis.db

# 服务器配置
HOST=0.0.0.0
PORT=8000
```

### 4. 初始化数据库

```bash
cd backend
python data.py
```

### 5. 启动后端服务

```bash
cd backend
python main.py
```

后端服务将在 `http://localhost:8000` 启动。

### 6. 启动前端服务

1. 在 VSCode 中打开项目
2. 右键点击 `frontend/index.html`
3. 选择 "Open with Live Server"
4. 浏览器将自动打开 `http://127.0.0.1:5500/frontend/index.html`

## 📖 功能说明

### 1. 台风路径可视化

- 在地图上显示台风的移动路径
- 支持按年份筛选台风数据
- 点击台风列表项可在地图上高亮显示路径
- 支持地图缩放和平移

### 2. 台风数据查询

- 查询指定台风的详细信息
- 支持按台风 ID、年份、状态筛选
- 显示台风的基本信息和路径点数据

### 3. 智能预测

- 基于历史数据预测台风未来路径
- 输入台风 ID 和预测小时数
- 返回预测的路径点坐标

### 4. 图像分析

- 支持两种方式上传图像：
  - URL 方式：输入图像 URL
  - 本地文件：上传本地图片（最大 10MB）
- 支持格式：JPG, PNG, GIF, WebP, BMP
- AI 分析卫星云图，识别台风特征

### 5. 报告生成

- 选择报告类型：简要报告 / 详细报告
- 选择 AI 提供商：通义千问 / DeepSeek
- 自动生成台风分析报告
- 支持 Markdown 格式化显示

---

## 🔧 配置说明

### Live Server 配置

项目已包含 `.vscode/settings.json` 配置文件，解决了 POST 请求导致页面刷新的问题：

```json
{
  "liveServer.settings.fullReload": false,
  "liveServer.settings.wait": 1000
}
```

**重要**: 如果使用 Live Server，请确保此配置文件存在。

---

## 📡 API 文档

后端服务启动后，可以访问以下地址查看完整的 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 主要 API 端点

- `GET /api/typhoons` - 获取台风列表
- `GET /api/typhoons/{typhoon_id}` - 获取台风详情
- `POST /api/prediction/path` - 台风路径预测
- `POST /api/analysis/satellite-image` - 卫星图像分析
- `POST /api/report/generate` - 生成台风报告

---

## ⚠️ 注意事项

### 1. Live Server POST 请求问题

如果使用 Live Server 时遇到 POST 请求导致页面刷新的问题，请确保：

- `.vscode/settings.json` 配置文件存在
- `liveServer.settings.fullReload` 设置为 `false`
- 重启 Live Server 使配置生效

### 2. CORS 配置

后端已配置 CORS 允许跨域请求，支持本地开发环境。

### 3. AI API 密钥

- 需要有效的通义千问和 DeepSeek API 密钥
- 在 `.env` 文件中配置密钥
- 未配置密钥时，AI 功能将无法使用

### 4. 数据库

- 首次运行需要执行 `python data.py` 初始化数据库
- 数据库文件位于 `backend/typhoon_analysis.db`
- 包含示例台风数据

## 👨‍💻 开发者

台风分析系统开发团队

**最后更新**: 2026-01-06
