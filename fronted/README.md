# 台风分析系统 - 前端应用

<p align="center">
  <img src="https://img.shields.io/badge/React-18-61DAFB.svg" alt="React 18">
  <img src="https://img.shields.io/badge/Vite-5.0-646CFF.svg" alt="Vite 5.0">
  <img src="https://img.shields.io/badge/Ant%20Design-6.x-1677FF.svg" alt="Ant Design">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
</p>

## 项目简介

台风分析系统前端是一个基于 **React 18** 构建的现代化数据可视化平台，专注于台风路径展示、智能预测、数据分析和交互式可视化。系统采用模块化架构设计，支持多维度数据展示和实时交互。

### 核心特性

- **交互式地图可视化** - 基于 Leaflet 的台风路径实时展示
- **智能预测可视化** - AI 预测路径与置信度展示
- **多维度数据分析** - ECharts 图表统计与对比
- **AI 智能客服** - 集成多模型对话系统
- **图像智能分析** - 卫星云图 AI 识别
- **响应式设计** - 适配多种屏幕尺寸

## 技术栈

### 核心框架
| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18.x | UI 框架 |
| Vite | 5.0 | 构建工具 |
| React Router | 7.x | 路由管理 |
| Axios | 1.6 | HTTP 客户端 |

### UI 组件库
| 技术 | 版本 | 用途 |
|------|------|------|
| Ant Design | 6.x | 基础组件库 |
| Ant Design X | 2.x | AI 对话组件 |
| Ant Design Charts | 2.x | 统计图表 |

### 可视化技术
| 技术 | 版本 | 用途 |
|------|------|------|
| Leaflet | 1.9 | 地图可视化 |
| React-Leaflet | 4.2 | React 地图组件 |
| ECharts | 6.0 | 数据图表 |
| D3.js | 7.x | 高级可视化 |

## 项目结构

```
fronted/
├── public/                     # 静态资源
│   └── vite.svg               # 应用图标
├── src/
│   ├── components/            # React 组件
│   │   ├── AIAgent.jsx               # AI 智能客服
│   │   ├── AIAgentButton.jsx         # AI 客服悬浮按钮
│   │   ├── AlertBanner.jsx           # 预警横幅
│   │   ├── AlertCenter.jsx           # 预警管理中心
│   │   ├── AvatarUpload.jsx          # 头像上传
│   │   ├── Header.jsx                # 页面头部导航
│   │   ├── ImageAnalysis.jsx         # 图像分析
│   │   ├── Login.jsx                 # 登录页面
│   │   ├── MapVisualization.jsx      # 地图可视化
│   │   ├── Prediction.jsx            # 台风预测
│   │   ├── PredictionVisualization.jsx # 预测可视化
│   │   ├── Register.jsx              # 注册页面
│   │   ├── ReportGeneration.jsx      # 报告生成
│   │   ├── StatisticsPanel.jsx       # 统计分析
│   │   ├── TabNavigation.jsx         # 标签导航
│   │   ├── TyphoonList.jsx           # 台风列表
│   │   ├── TyphoonQuery.jsx          # 台风查询
│   │   └── UserCenter.jsx            # 用户中心
│   ├── pictures/              # 图片资源
│   │   ├── deepseek.png       # DeepSeek 图标
│   │   └── taifeng.gif        # 台风动画
│   ├── services/              # API 服务层
│   │   ├── api.js             # API 调用封装
│   │   ├── ossConfig.js       # OSS 配置
│   │   ├── ossUploadService.js # OSS 上传服务
│   │   └── ossUtils.js        # OSS 工具函数
│   ├── styles/                # 样式文件
│   │   ├── AIAgent.css        # AI 客服样式
│   │   ├── AIAgentButton.css  # AI 按钮样式
│   │   ├── AlertCenter.css    # 预警中心样式
│   │   ├── Auth.css           # 认证页面样式
│   │   ├── AvatarUpload.css   # 头像上传样式
│   │   ├── Header.css         # 头部样式
│   │   ├── ImageAnalysis.css  # 图像分析样式
│   │   ├── MapVisualization.css # 地图可视化样式
│   │   ├── ReportGeneration.css # 报告生成样式
│   │   ├── StatisticsPanel.css  # 统计分析样式
│   │   ├── TyphoonQuery.css   # 台风查询样式
│   │   ├── common.css         # 通用样式
│   │   └── index.css          # 主样式文件
│   ├── App.jsx                # 根组件
│   └── main.jsx               # 应用入口
├── .eslintrc.cjs             # ESLint 配置
├── index.html                # HTML 模板
├── package.json              # 项目依赖
└── vite.config.js            # Vite 配置
```

## 核心功能模块

### 1. 台风路径可视化

**组件**: `MapVisualization.jsx`

基于 Leaflet 的交互式地图，支持多台风路径叠加显示。

**功能特性**:
- 实时路径绘制与动画
- 强度等级颜色编码
- 风速大小映射
- 多台风叠加对比
- 年份筛选 (2000-2026)
- 悬浮信息展示

**颜色规范**:
| 强度等级 | 颜色 | 风速范围 |
|----------|------|----------|
| 热带低压 | `#3498db` | < 17.2 m/s |
| 热带风暴 | `#2ecc71` | 17.2-24.4 m/s |
| 强热带风暴 | `#f1c40f` | 24.5-32.6 m/s |
| 台风 | `#e67e22` | 32.7-41.4 m/s |
| 强台风 | `#e74c3c` | 41.5-50.9 m/s |
| 超强台风 | `#c0392b` | ≥ 51.0 m/s |

### 2. 预测可视化

**组件**: `PredictionVisualization.jsx`

AI 预测路径可视化，展示未来 24/48/72 小时预测结果。

**功能特性**:
- 点击路径点触发预测
- 红色虚线预测路径
- 预测点强度可视化
- 置信度展示
- 预测结果面板

### 3. AI 智能客服

**组件**: `AIAgent.jsx`

集成多模型 AI 对话系统。

**模型支持**:
| 模型 | 特点 | 深度思考 |
|------|------|----------|
| DeepSeek-R1 | 深度推理 | 支持 |
| DeepSeek-V3 | 通用对话 | - |
| GLM-4 | 中文优化 | - |
| Qwen | 多模态 | - |

**功能**:
- 实时对话交互
- 会话历史管理
- 热门问题推荐
- 模型自动降级

### 4. 图像分析

**组件**: `ImageAnalysis.jsx`

卫星云图智能分析。

**分析模式**:
- **基础模式** - 快速特征提取
- **高级模式** - 详细结构分析
- **OpenCV 模式** - 传统算法
- **融合模式** - 综合方法

### 5. 统计分析

**组件**: `StatisticsPanel.jsx`

多维度数据统计与可视化。

**图表类型**:
- 年度趋势折线图
- 月度分布柱状图
- 强度等级饼图
- 路径热力图

## 快速开始

### 环境要求

- Node.js >= 16.0.0
- npm >= 8.0.0 或 yarn >= 1.22.0
- 后端服务已启动

### 安装步骤

1. **进入项目目录**

```bash
cd fronted
```

2. **安装依赖**

```bash
npm install
# 或
yarn install
```

3. **配置代理**

编辑 `vite.config.js` 确保代理配置正确：

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    }
  }
}
```

4. **启动开发服务器**

```bash
npm run dev
# 或
yarn dev
```

访问 `http://localhost:5173`

### 生产构建

```bash
# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 开发指南

### 代码规范

- **组件命名**: PascalCase (如 `MapVisualization.jsx`)
- **函数命名**: camelCase (如 `getTyphoonList`)
- **常量命名**: UPPER_SNAKE_CASE (如 `API_BASE_URL`)
- **缩进**: 2 空格
- **引号**: 单引号

### 组件开发示例

```jsx
import React, { useState, useEffect } from 'react';
import { Card } from 'antd';

const TyphoonCard = ({ typhoon }) => {
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // 组件挂载逻辑
  }, []);

  return (
    <Card loading={loading} title={typhoon.name}>
      {/* 组件内容 */}
    </Card>
  );
};

export default TyphoonCard;
```

### API 调用示例

```javascript
import { getTyphoonList, predictPath } from '../services/api';

// 获取台风列表
const typhoons = await getTyphoonList({ year: 2024 });

// 预测路径
const prediction = await predictPath('202001', 48);
```

## API 接口

### 台风数据

```javascript
// 获取台风列表
getTyphoonList(params)
// params: { year, status, search, limit }

// 获取台风详情
getTyphoonById(typhoonId)

// 获取台风路径
getTyphoonPath(typhoonId)
```

### 预测服务

```javascript
// 路径预测
predictPath(typhoonId, hours)
// hours: 24 | 48 | 72

// 任意起点预测
predictFromArbitraryStart(data)
```

### AI 客服

```javascript
// 发送消息
askAIQuestion(sessionId, question, model, deepThinking)

// 获取会话列表
getAISessions()

// 获取热门问题
getAIQuestions()
```

## 样式规范

### 主题色

```css
:root {
  --primary-color: #667eea;
  --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --success-color: #52c41a;
  --warning-color: #faad14;
  --error-color: #f5222d;
}
```

### 响应式断点

| 断点 | 宽度 | 设备 |
|------|------|------|
| xs | < 576px | 手机 |
| sm | ≥ 576px | 平板 |
| md | ≥ 768px | 笔记本 |
| lg | ≥ 992px | 桌面 |
| xl | ≥ 1200px | 大屏 |

## 性能优化

### 代码分割

```jsx
import { lazy, Suspense } from 'react';

const AIAgent = lazy(() => import('./components/AIAgent'));

<Suspense fallback={<Loading />}>
  <AIAgent />
</Suspense>
```

### 图片优化

- 使用 WebP 格式
- 懒加载非首屏图片
- 压缩图片资源

### 缓存策略

- 组件级缓存 (React.memo)
- 数据缓存 (SWR/React Query)
- 浏览器缓存

## 常见问题

### Q: 地图无法加载？

A: 检查网络连接和瓦片服务配置。默认使用高德地图瓦片。

### Q: API 请求失败？

A: 确保后端服务已启动，并检查 Vite 代理配置。

### Q: 构建失败？

A: 检查 Node.js 版本是否 >= 16，并清除 node_modules 重新安装。

```bash
rm -rf node_modules
npm install
```

## 更新日志

### v1.0.0 (2026-02-08)

- 完成 React 18 架构升级
- 实现台风路径可视化
- 添加 AI 预测可视化
- 集成 AI 智能客服
- 实现图像分析功能
- 完善用户认证系统

## 浏览器支持

| 浏览器 | 最低版本 |
|--------|----------|
| Chrome | 90+ |
| Firefox | 88+ |
| Safari | 14+ |
| Edge | 90+ |

## 许可证

MIT License © 2026 TyphoonAnalysis Team
