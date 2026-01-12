# 台风分析系统 - 前端文档

## 📋 项目简介

台风分析系统前端是一个基于 **React** 构建的现代化Web应用，提供台风数据可视化、统计分析、路径预测等功能。采用响应式设计，支持多种数据展示方式。

## 🚀 技术栈

- **框架**: React 18
- **地图可视化**: Leaflet + React-Leaflet
- **图表库**: ECharts
- **HTTP客户端**: Axios
- **路由**: React Router DOM
- **构建工具**: Vite
- **样式**: CSS3 + 内联样式

## 📁 项目结构

```
service/
├── public/                 # 静态资源
├── src/
│   ├── components/        # React组件
│   │   ├── MapVisualization.jsx      # 地图可视化组件
│   │   ├── StatisticsPanel.jsx       # 统计分析面板
│   │   ├── PredictionPanel.jsx       # 预测功能面板
│   │   └── AlertPanel.jsx            # 预警管理面板
│   ├── services/          # API服务层
│   │   └── api.js         # API调用封装
│   ├── styles/            # 全局样式
│   │   └── index.css      # 主样式文件
│   ├── App.jsx            # 根组件
│   └── main.jsx           # 应用入口
├── package.json           # 项目依赖配置
├── vite.config.js         # Vite配置
└── README.md              # 本文档
```

## 🛠️ 安装与运行

### 环境要求

- Node.js >= 16.0.0
- npm >= 8.0.0 或 yarn >= 1.22.0

### 安装依赖

```bash
# 进入前端目录
cd service

# 安装依赖
npm install
# 或使用 yarn
yarn install
```

### 开发模式

```bash
# 启动开发服务器
npm run dev
# 或
yarn dev
```

访问 `http://localhost:5173` 查看应用

### 生产构建

```bash
# 构建生产版本
npm run build
# 或
yarn build

# 预览生产构建
npm run preview
# 或
yarn preview
```

## 🎯 核心功能

### 1. 台风路径可视化

**文件**: `src/components/MapVisualization.jsx`

**功能特性**:
- 🗺️ 基于Leaflet的交互式地图
- 📍 台风路径实时绘制
- 🎨 根据强度等级显示不同颜色
- 📊 路径点大小反映风速强度
- 🔍 支持多台风叠加显示
- 📅 年份筛选（2000-2026年）
- 🔎 台风名称/ID搜索
- 📌 悬浮显示详细信息（时间、位置、气压、风速等）

**使用说明**:
1. 左侧面板选择年份和状态筛选台风
2. 点击台风卡片在地图上显示路径
3. 勾选"多��风叠加显示"可同时查看多个台风
4. 鼠标悬停在路径点上查看详细信息

### 2. 统计分析

**文件**: `src/components/StatisticsPanel.jsx`

**功能特性**:
- 📈 台风数量统计（按年份、月份、强度）
- 📊 ECharts图表可视化
- 📥 数据导出（JSON/CSV格式）
- 🔢 支持单个/批量导出
- ✅ 可选包含路径数据

**图表类型**:
- 年度台风数量趋势图
- 月度分布柱状图
- 强度等级饼图

### 3. 台风预测

**文件**: `src/components/PredictionPanel.jsx`

**功能特性**:
- 🤖 基于AI模型的路径预测
- 📍 预测未来24/48/72小时路径
- 🎯 显示预测置信度
- 📊 预测结果可视化

### 4. 预警管理

**文件**: `src/components/AlertPanel.jsx`

**功能特性**:
- ⚠️ 台风预警信息管理
- 🔔 预警等级分类（蓝色/黄色/橙色/红色）
- 📝 预警详情查看
- 🗑️ 预警删除功能

## 🔌 API接口

### API配置

**文件**: `src/services/api.js`

**基础URL**: `http://localhost:8000/api`

### 主要接口

#### 1. 获取台风列表
```javascript
getTyphoonList(params)
// params: { year, status, limit }
```

#### 2. 获取台风路径
```javascript
getTyphoonPath(typhoonId)
```

#### 3. 统计分析
```javascript
getStatistics(params)
// params: { startYear, endYear, groupBy }
```

#### 4. 数据导出
```javascript
exportTyphoonData(typhoonId, includePath)
exportBatchTyphoonData(params)
```

#### 5. 台风预测
```javascript
predictTyphoonPath(typhoonId, hours)
```

#### 6. 预警管理
```javascript
getAlerts()
createAlert(data)
deleteAlert(alertId)
```

## 🎨 样式规范

### 颜色方案

**强度等级颜色**:
- 热带低压: `#3498db` (蓝色)
- 热带风暴: `#2ecc71` (绿色)
- 强热带风暴: `#f1c40f` (黄色)
- 台风: `#e67e22` (橙色)
- 强台风: `#e74c3c` (红色)
- 超强台风: `#c0392b` (深红色)

**主题色**:
- 主色调: `#667eea` (紫色)
- 渐变色: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`

### 路径点大小规则

- 风速 < 20 m/s: 半径 4px
- 风速 20-30 m/s: 半径 6px
- 风速 30-40 m/s: 半径 8px
- 风速 40-50 m/s: 半径 10px
- 风速 > 50 m/s: 半径 12px

## 🐛 常见问题

### 1. 地图无法加载

**原因**: 瓦片服务访问失败

**解决方案**: 
- 检查网络连接
- 当前使用高德地图瓦片服务（国内稳定）
- 如需切换，修改 `MapVisualization.jsx` 中的 `TileLayer` URL

### 2. API请求失败

**原因**: 后端服务未启动或端口不匹配

**解决方案**:
```bash
# 确保后端服务运行在 http://localhost:8000
cd ../backend
python main.py
```

### 3. 查询不到历史年份数据

**原因**: 
- 数据库中没有历史数据
- API参数传递错误

**解决方案**:
- 运行后端数据导入脚本
- 检查浏览器控制台Network面板确认API请求参数

## 📝 开发规范

### 代码风格

- 使用 4 空格缩进
- 组件使用函数式组件 + Hooks
- 使用 ES6+ 语法
- 遵循 React 最佳实践

### 命名规范

- 组件文件: PascalCase (如 `MapVisualization.jsx`)
- 工具函数: camelCase (如 `getTyphoonList`)
- 常量: UPPER_SNAKE_CASE (如 `API_BASE_URL`)

### Git提交规范

```
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式调整
refactor: 重构
perf: 性能优化
test: 测试相关
chore: 构建/工具链相关
```

## 🔄 更新日志

### v1.0.0 (2026-01-12)
- ✅ 完成台风路径可视化功能
- ✅ 实现统计分析面板
- ✅ 添加数据导出功能
- ✅ 支持年份筛选（2000-2026年）
- ✅ 修复API参数传递问题
- ✅ 优化地图性能

## 📞 技术支持

如有问题或建议，请联系开发团队或提交Issue。

## 📄 许可证

MIT License

