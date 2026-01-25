# 台风分析系统 - 前端文档

## 📋 项目简介

台风分析系统前端是一个基于 **React 18** 构建的现代化 Web 应用，提供台风数据可视化、统计分析、路径预测、AI 智能客服、图像分析等功能。采用响应式设计，支持多种数据展示方式，集成 Ant Design X 组件库。

## 🚀 技术栈

- **框架**: React 18
- **UI 组件库**: Ant Design + Ant Design X
- **地图可视化**: Leaflet + React-Leaflet
- **图表库**: ECharts
- **HTTP 客户端**: Axios
- **路由**: React Router DOM
- **构建工具**: Vite
- **样式**: CSS3 + 内联样式

## 📁 项目结构

```
service/
├── public/                 # 静态资源
├── src/
│   ├── components/        # React 组件
│   │   ├── MapVisualization.jsx      # 地图可视化组件
│   │   ├── StatisticsPanel.jsx       # 统计分析面板
│   │   ├── PredictionPanel.jsx       # 预测功能面板
│   │   ├── AlertPanel.jsx            # 预警管理面板
│   │   ├── AIAgent.jsx               # AI 智能客服
│   │   └── ImageAnalysis.jsx         # 图像分析面板
│   ├── services/          # API 服务层
│   │   └── api.js         # API 调用封装
│   ├── styles/            # 全局样式
│   │   ├── index.css      # 主样式文件
│   │   └── AIAgent.css    # AI 客服样式
│   ├── App.jsx            # 根组件
│   └── main.jsx           # 应用入口
├── package.json           # 项目依赖配置
├── vite.config.js         # Vite 配置
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

- 🗺️ 基于 Leaflet 的交互式地图
- 📍 台风路径实时绘制
- 🎨 根据强度等级显示不同颜色
- 📊 路径点大小反映风速强度
- 🔍 支持多台风叠加显示
- 📅 年份筛选（2000-2026 年）
- 🔎 台风名称/ID 搜索
- 📌 悬浮显示详细信息（时间、位置、气压、风速等）

**使用说明**:

1. 左侧面板选择年份和状态筛选台风
2. 点击台风卡片在地图上显示路径
3. 勾选"多 �� 风叠加显示"可同时查看多个台风
4. 鼠标悬停在路径点上查看详细信息

### 2. 统计分析

**文件**: `src/components/StatisticsPanel.jsx`

**功能特性**:

- 📈 台风数量统计（按年份、月份、强度）
- 📊 ECharts 图表可视化
- 📥 数据导出（JSON/CSV 格式）
- 🔢 支持单个/批量导出
- ✅ 可选包含路径数据

**图表类型**:

- 年度台风数量趋势图
- 月度分布柱状图
- 强度等级饼图

### 3. 台风预测

**文件**: `src/components/PredictionPanel.jsx`

**功能特性**:

- 🤖 基于 AI 模型的路径预测
- 📍 预测未来 24/48/72 小时路径
- 🎯 显示预测置信度
- 📊 预测结果可视化

### 4. 预警管理

**文件**: `src/components/AlertPanel.jsx`

**功能特性**:

- ⚠️ 台风预警信息管理
- 🔔 预警等级分类（蓝色/黄色/橙色/红色）
- 📝 预警详情查看
- 🗑️ 预警删除功能
- 🔍 按台风 ID 或等级筛选

### 5. AI 智能客服

**文件**: `src/components/AIAgent.jsx`

**功能特性**:

- 🤖 集成多个 AI 模型（DeepSeek、GLM、Qwen）
- 🧠 支持深度思考模式（DeepSeek-R1）
- 💬 实时对话交互
- 📝 对话历史记录管理
- 🔥 热门问题快速回复
- 🔄 模型自动降级和重试机制
- 📋 会话列表管理

**使用说明**:

1. 点击"AI 客服"进入对话界面
2. 选择 AI 模型（DeepSeek/GLM/Qwen）
3. 开启/关闭"深度思考"模式
   - 开启：使用 DeepSeek-R1 深度思考模型（更准确但较慢）
   - 关闭：使用常规模型（更快）
4. 输入问题并发送
5. 查看 AI 回答和对话历史
6. 可点击热门问题快速提问

**深度思考模式说明**:

- 当开启深度思考模式时，无论选择哪个模型，都会使用 DeepSeek-R1 深度思考模型
- 深度思考模式提供更详细的推理过程和更准确的答案
- 响应时间会比常规模式长

### 6. 图像分析

**文件**: `src/components/ImageAnalysis.jsx`

**功能特性**:

- 🖼️ 卫星云图上传和管理
- 🔍 多种分析模式（基础/高级/OpenCV/融合）
- 🤖 AI 模型智能分析（Qwen-VL、GLM-4V）
- 📊 提取台风特征（中心位置、云系结构、强度估计）
- 📷 支持红外/可见光图像
- 📋 图像历史记录查看

**使用说明**:

1. 进入"图像分析"面板
2. 上传卫星云图（支持 JPG、PNG 格式）
3. 选择分析模式：
   - **基础模式**：快速分析，提供基本信息
   - **高级模式**：详细分析，包含更多特征
   - **OpenCV 模式**：使用计算机视觉算法
   - **融合模式**：结合多种方法的综合分析
4. 选择 AI 模型（Qwen-VL 或 GLM-4V）
5. 点击"开始分析"
6. 查看分析结果和提取的台风特征

## 🔌 API 接口

### API 配置

**文件**: `src/services/api.js`

**基础 URL**: `http://localhost:8000/api`

### 主要接口

#### 1. 获取台风列表

```javascript
getTyphoonList(params);
// params: { year, status, limit }
```

#### 2. 获取台风路径

```javascript
getTyphoonPath(typhoonId);
```

#### 3. 统计分析

```javascript
getStatistics(params);
// params: { startYear, endYear, groupBy }
```

#### 4. 数据导出

```javascript
exportTyphoonData(typhoonId, includePath);
exportBatchTyphoonData(params);
```

#### 5. 台风预测

```javascript
predictTyphoonPath(typhoonId, hours);
```

#### 6. 预警管理

```javascript
getAlerts();
createAlert(data);
deleteAlert(alertId);
```

#### 7. AI 智能客服

```javascript
// 创建对话会话
createAISession(title);

// 获取会话列表
getAISessions();

// 获取会话历史
getAISessionHistory(sessionId);

// 发送问题获取回答
askAIQuestion(sessionId, question, model, deepThinking);
// 参数:
// - sessionId: 会话 ID
// - question: 用户问题
// - model: AI 模型 (deepseek/glm/qwen)
// - deepThinking: 是否启用深度思考模式 (boolean)

// 获取热门问题
getHotQuestions();
```

#### 8. 图像分析

```javascript
// 上传图像
uploadImage(formData);
// formData 包含: file, typhoon_id, image_type, description

// 分析图像
analyzeImage(imageId, analysisMode, model);
// 参数:
// - imageId: 图像 ID
// - analysisMode: 分析模式 (basic/advanced/opencv/fusion)
// - model: AI 模型 (qwen-vl/glm-4v)

// 获取台风图像列表
getTyphoonImages(typhoonId);
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

### 2. API 请求失败

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
- API 参数传递错误

**解决方案**:

- 运行后端数据导入脚本
- 检查浏览器控制台 Network 面板确认 API 请求参数

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

### Git 提交规范

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

### v2.0.0 (2026-01-13)

**新增功能**:

- ✅ AI 智能客服系统（支持 DeepSeek、GLM、Qwen）
- ✅ 深度思考模式（DeepSeek-R1）
- ✅ 图像分析功能（卫星云图分析）
- ✅ 多种图像分析模式（基础/高级/OpenCV/融合）
- ✅ 对话历史管理
- ✅ 热门问题快速回复
- ✅ 集成 Ant Design X 组件库

**优化改进**:

- ✅ 优化前后端交互逻辑
- ✅ 改进错误处理机制
- ✅ 增强用户体验
- ✅ 优化组件性能

### v1.0.0 (2026-01-12)

**核心功能**:

- ✅ 完成台风路径可视化功能
- ✅ 实现统计分析面板
- ✅ 添加数据导出功能
- ✅ 支持年份筛选（2000-2026 年）
- ✅ 修复 API 参数传递问题
- ✅ 优化地图性能

## 📞 技术支持

如有问题或建议，请联系开发团队或提交 Issue。

## 📄 许可证

MIT License
