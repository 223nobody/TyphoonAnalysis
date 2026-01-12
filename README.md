# 🌀 台风分析系统 (Typhoon Analysis System)

## 📋 项目简介

台风分析系统是一个基于 **FastAPI + React + AI** 的智能台风数据分析与可视化平台。系统集成了台风数据爬取、实时监控、路径可视化、统计分析、智能预测、预警管理等功能，为气象研究和防灾减灾提供数据支持。

## ✨ 核心特性

### 🗺️ 台风路径可视化
- 基于Leaflet的交互式地图展示
- 支持多台风路径叠加显示
- 根据强度等级动态着色
- 实时路径点详情查看
- 年份范围：2000-2026年

### 📊 统计分析
- 多维度数据统计（年度/月度/强度）
- ECharts图表可视化
- 趋势分析与对比
- 数据导出（JSON/CSV）

### 🤖 智能预测
- 基于AI模型的路径预测
- 支持24/48/72小时预测
- 预测置信度评估
- 预测结果可视化

### ⚠️ 预警管理
- 多级别预警系统（蓝/黄/橙/红）
- 预警信息发布与管理
- 区域预警覆盖
- 预警历史记录

### 🕷️ 自动数据爬取
- 定时爬取中国气象局数据
- 自动更新活跃台风信息
- 历史数据补充
- 失败重试机制

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                     前端层 (Frontend)                    │
│  React 18 + Leaflet + ECharts + Axios + Vite           │
│  端口: 5173                                             │
└─────────────────────────────────────────────────────────┘
                            ↓ HTTP/REST API
┌─────────────────────────────────────────────────────────┐
│                     后端层 (Backend)                     │
│  FastAPI + SQLAlchemy + APScheduler + aiohttp          │
│  端口: 8000                                             │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   数据层 (Database)                      │
│  SQLite (开发) / PostgreSQL (生产)                      │
│  表: typhoons, typhoon_paths, alerts, predictions      │
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
│   │   │   └── crawler.py     # 爬虫API
│   │   ├── core/              # 核心配置
│   │   │   ├── config.py      # 应用配置
│   │   │   └── database.py    # 数据库配置
│   │   ├── models/            # 数据模型
│   │   ├── schemas/           # Pydantic模式
│   │   └── services/          # 业务逻辑
│   │       ├── crawler.py     # 爬虫服务
│   │       ├── scheduler.py   # 定时任务
│   │       └── predictor.py   # 预测服务
│   ├── main.py                # 应用入口
│   ├── data.py                # 数据导入脚本
│   ├── requirements.txt       # Python依赖
│   └── README.md              # 后端文档
│
├── service/                    # 前端应用
│   ├── src/
│   │   ├── components/        # React组件
│   │   │   ├── MapVisualization.jsx    # 地图可视化
│   │   │   ├── StatisticsPanel.jsx     # 统计分析
│   │   │   ├── PredictionPanel.jsx     # 预测功能
│   │   │   └── AlertPanel.jsx          # 预警管理
│   │   ├── services/          # API服务
│   │   │   └── api.js         # API封装
│   │   ├── styles/            # 样式文件
│   │   ├── App.jsx            # 根组件
│   │   └── main.jsx           # 入口文件
│   ├── package.json           # Node依赖
│   ├── vite.config.js         # Vite配置
│   └── README.md              # 前端文档
│
└── README.md                   # 项目总文档（本文件）
```

## 🚀 快速开始

### 环境要求

**后端**:
- Python >= 3.10
- pip >= 21.0

**前端**:
- Node.js >= 16.0
- npm >= 8.0 或 yarn >= 1.22

### 安装步骤

#### 1. 克隆项目

```bash
git clone <repository-url>
cd TyphoonAnalysis
```

#### 2. 启动后端服务

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

# 启动服务
python main.py
```

后端服务将在 `http://localhost:8000` 启动

#### 3. 启动前端应用

```bash
# 打开新终端，进入前端目录
cd service

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

#### 4. 访问应用

- **前端界面**: http://localhost:5173
- **后端API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 📖 使用指南

### 1. 台风路径可视化

1. 访问前端首页，点击"台风路径可视化"
2. 在左侧面板选择年份（2000-2026）
3. 可选择台风状态筛选（活跃/已停止）
4. 点击台风卡片在地图上显示路径
5. 勾选"多台风叠加显示"可同时查看多个台风
6. 鼠标悬停在路径点上查看详细信息

### 2. 统计分析

1. 点击"统计分析"进入分析面板
2. 选择统计类型（年度/月度/强度）
3. 设置年份范围
4. 点击"查询"生成图表
5. 可导出统计数据（JSON/CSV格式）

### 3. 台风预测

1. 进入"台风预测"面板
2. 选择要预测的台风
3. 设置预测时长（24/48/72小时）
4. 点击"开始预测"
5. 查看预测路径和置信度

### 4. 预警管理

1. 进入"预警管理"面板
2. 查看当前所有预警信息
3. 可按台风ID或预警等级筛选
4. 点击"查看详情"了解预警详情
5. 管理员可创建或删除预警

### 5. 数据导出

1. 在统计分析或台风详情页面
2. 点击"导出数据"按钮
3. 选择导出格式（JSON/CSV）
4. 勾选是否包含路径数据
5. 下载导出文件

## 🔌 API接口

### 基础信息

- **Base URL**: `http://localhost:8000/api`
- **文档地址**: `http://localhost:8000/docs`
- **认证方式**: 暂无（开发环境）

### 主要端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/typhoons` | GET | 获取台风列表 |
| `/typhoons/{id}` | GET | 获取台风详情 |
| `/typhoons/{id}/path` | GET | 获取台风路径 |
| `/statistics` | GET | 获取统计数据 |
| `/export/typhoon/{id}` | GET | 导出台风数据 |
| `/export/batch` | POST | 批量导出 |
| `/predictions/predict` | POST | 预测台风路径 |
| `/alerts` | GET | 获取预警列表 |
| `/alerts` | POST | 创建预警 |
| `/crawler/trigger` | POST | 触发爬虫 |

详细API文档请访问: http://localhost:8000/docs

## 🎨 界面预览

### 台风路径可视化
- 交互式地图展示台风路径
- 颜色编码表示强度等级
- 路径点大小反映风速

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
cd service

# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 预览构建
npm run preview
```

详见: [service/README.md](service/README.md)

## 📊 数据说明

### 台风强度等级

| 等级 | 风速范围 | 颜色 |
|------|----------|------|
| 热带低压 | < 17.2 m/s | 蓝色 |
| 热带风暴 | 17.2-24.4 m/s | 绿色 |
| 强热带风暴 | 24.5-32.6 m/s | 黄色 |
| 台风 | 32.7-41.4 m/s | 橙色 |
| 强台风 | 41.5-50.9 m/s | 红色 |
| 超强台风 | ≥ 51.0 m/s | 深红色 |

### 数据来源

- **主要数据源**: 中国气象局台风网
- **更新频率**: 每小时自动爬取
- **历史数据**: 2000年至今
- **数据准确性**: 官方权威数据

## 🐛 常见问题

### 1. 后端启动失败

**问题**: `ModuleNotFoundError: No module named 'xxx'`

**解决**:
```bash
pip install -r requirements.txt
```

### 2. 前端无法连接后端

**问题**: `Network Error` 或 `CORS Error`

**解决**:
- 确认后端服务已启动（http://localhost:8000）
- 检查防火墙设置
- 查看后端CORS配置

### 3. 地图无法加载

**问题**: 地图瓦片加载失败

**解决**:
- 检查网络连接
- 当前使用高德地图瓦片（国内稳定）
- 可在代码中切换其他瓦片服务

### 4. 查询不到历史数据

**问题**: 选择历史年份无数据

**解决**:
```bash
# 运行数据导入脚本
cd backend
python data.py
```

### 5. 数据库锁定错误

**问题**: `database is locked`

**解决**:
- SQLite不支持高并发
- 生产环境建议使用PostgreSQL
- 减少并发写入操作

## 🔒 安全建议

### 开发环境
- ✅ DEBUG模式开启
- ✅ CORS允许所有来源
- ✅ 无需认证

### 生产环境
- ⚠️ 关闭DEBUG模式
- ⚠️ 配置CORS白名单
- ⚠️ 添加API认证（JWT/OAuth）
- ⚠️ 使用HTTPS
- ⚠️ 添加限流保护
- ⚠️ 使用PostgreSQL替代SQLite
- ⚠️ 配置日志监控

## 📈 性能优化

### 后端优化
- 使用异步数据库操作
- 添加数据库索引
- 实现响应缓存
- 启用GZIP压缩
- 使用连接池

### 前端优化
- 组件懒加载
- 图片压缩
- 代码分割
- 使用CDN
- 启用浏览器缓存

## 🔄 版本历史

### v1.0.0 (2026-01-12)
- ✅ 完成核心功能开发
- ✅ 台风路径可视化
- ✅ 统计分析功能
- ✅ 数据导出功能
- ✅ 预警管理系统
- ✅ 自动数据爬取
- ✅ 年份筛选（2000-2026）
- ✅ 修复API参数传递问题
- ✅ 优化前后端交互

### 未来计划
- 🔲 移动端适配
- 🔲 实时推送通知
- 🔲 用户权限管理
- 🔲 更多AI预测模型
- 🔲 国际化支持
- 🔲 数据可视化增强

## 👥 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

### 代码规范

- Python: 遵循PEP 8
- JavaScript: 使用4空格缩进
- 提交信息: 使用约定式提交格式

## 📞 联系方式

- **项目维护**: 开发团队
- **问题反馈**: 提交Issue
- **技术支持**: 查看文档或联系开发团队

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- 感谢中国气象局提供台风数据
- 感谢开源社区的优秀项目
- 感谢所有贡献者的支持

---

**⚡ 快速链接**

- [前端文档](service/README.md)
- [后端文档](backend/README.md)
- [API文档](http://localhost:8000/docs)
- [问题反馈](https://github.com/your-repo/issues)

**🌟 如果这个项目对您有帮助，请给我们一个Star！**

