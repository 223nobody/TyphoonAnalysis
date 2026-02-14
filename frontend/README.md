# 台风分析系统 - 前端应用

<p align="center">
  <img src="https://img.shields.io/badge/React-18-61DAFB.svg" alt="React 18">
  <img src="https://img.shields.io/badge/Vite-5.0-646CFF.svg" alt="Vite 5.0">
  <img src="https://img.shields.io/badge/Ant%20Design-6.x-1677FF.svg" alt="Ant Design">
  <img src="https://img.shields.io/badge/Voice%20Input-Supported-success.svg" alt="Voice Input">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
</p>

## 项目简介

台风分析系统前端是一个基于 **React 18** 构建的现代化数据可视化平台，专注于台风路径展示、智能预测、数据分析和交互式可视化。系统采用模块化架构设计，支持多维度数据展示和实时交互，并集成了**语音输入**功能，让用户可以通过语音与 AI 助手进行交互。

### 核心特性

- **交互式地图可视化** - 基于 Leaflet 的台风路径实时展示
- **智能预测可视化** - AI 预测路径与置信度展示
- **多维度数据分析** - ECharts 图表统计与对比
- **AI 智能客服** - 集成多模型对话系统，**支持语音输入**
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

### 音频处理
| 技术 | 用途 |
|------|------|
| Web Audio API | 浏览器音频录制 |
| MediaRecorder | 媒体流录制 |

## 项目结构

```
fronted/
├── public/                     # 静态资源
│   └── vite.svg               # 应用图标
├── src/
│   ├── components/            # React 组件
│   │   ├── AIAgent.jsx               # AI 智能客服 (含语音输入)
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
│   │   ├── api.js             # API 调用封装 (含 ASR 接口)
│   │   ├── ossConfig.js       # OSS 配置
│   │   ├── ossUploadService.js # OSS 上传服务
│   │   └── ossUtils.js        # OSS 工具函数
│   ├── styles/                # 样式文件
│   │   ├── AIAgent.css        # AI 客服样式 (含语音按钮)
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

### 3. AI 智能客服 (含语音输入)

**组件**: `AIAgent.jsx`

集成多模型 AI 对话系统，**支持语音输入功能**。

**模型支持**:
| 模型 | 特点 | 深度思考 |
|------|------|----------|
| DeepSeek-R1 | 深度推理 | 支持 |
| DeepSeek-V3 | 通用对话 | - |
| GLM-4 | 中文优化 | - |
| Qwen | 多模态 | - |

**功能**:
- 实时对话交互
- **语音输入**: 点击麦克风图标进行语音输入
- 会话历史管理
- 热门问题推荐
- 模型自动降级

#### 语音输入功能详解

**使用方式**:
1. 点击输入框右侧的麦克风图标
2. 开始说话，系统实时显示录音时长
3. 再次点击或等待 60 秒自动停止
4. 语音自动转换为文字并发送

**技术实现**:
- 使用 Web Audio API 进行音频采集
- 录制格式: WAV (16kHz, 16bit, 单声道)
- 后端使用 Qwen3-ASR 模型进行识别
- 支持中文、英文、粤语自动检测

**API 接口**:
```javascript
// 语音识别
import { transcribeAudio } from '../services/api';

const handleVoiceInput = async (audioBlob) => {
  try {
    const result = await transcribeAudio(audioBlob, 'auto');
    console.log('识别结果:', result.text);
  } catch (error) {
    console.error('语音识别失败:', error);
  }
};
```

**界面展示**:
- 录音按钮带脉冲动画效果
- 实时显示录音时长 (00:00 - 00:60)
- 录音状态视觉反馈

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
- 后端服务已启动 (包括 ASR 服务)

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

3. **配置代理** (开发环境)

`vite.config.js` 已配置代理：

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

4. **启动开发服务器**

```bash
npm run dev
# 或
yarn dev
```

访问 `http://localhost:5173`

### 构建生产版本

```bash
npm run build
# 或
yarn build
```

构建输出在 `dist/` 目录。

## API 服务层

### 封装说明

所有 API 调用统一封装在 `src/services/api.js`：

```javascript
// 台风数据
export const getTyphoonList = async (params) => { ... }
export const getTyphoonById = async (id) => { ... }

// AI 对话
export const sendChatMessage = async (message, model) => { ... }

// 语音识别 (新增)
export const transcribeAudio = async (audioBlob, language) => { ... }
export const checkASRHealth = async () => { ... }
```

### ASR 语音识别 API

**接口列表**:

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/asr/transcribe` | POST | 语音转文字 |
| `/api/asr/health` | GET | 服务健康检查 |
| `/api/asr/languages` | GET | 支持语言列表 |

**使用示例**:

```javascript
import { transcribeAudio } from './services/api';

// 录制音频后调用
const audioBlob = await recordAudio();
const result = await transcribeAudio(audioBlob, 'auto');
console.log(result.text); // 输出识别文字
```

## 组件开发指南

### AIAgent 组件

**文件**: `src/components/AIAgent.jsx`

**主要功能**:
- 多模型 AI 对话
- 语音输入支持
- 会话管理
- 消息历史

**语音输入实现**:

```javascript
// 开始录音
const startRecording = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mediaRecorder = new MediaRecorder(stream);
  // 处理音频数据...
};

// 停止录音并识别
const stopRecording = async () => {
  const audioBlob = await getRecordedAudio();
  const result = await transcribeAudio(audioBlob);
  setInputMessage(result.text);
};
```

**样式文件**: `src/styles/AIAgent.css`

```css
/* 语音输入按钮 */
.voice-input-button {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  /* ... */
}

.voice-input-button.recording {
  width: auto;
  min-width: 72px;
  border-radius: 18px;
  /* 显示计时器 */
}

.recording-time {
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 13px;
}
```

## 开发规范

### 代码风格

- 使用 ESLint 进行代码检查
- 使用 Prettier 进行代码格式化
- 组件使用函数式组件 + Hooks

### 命名规范

- 组件: PascalCase (如 `AIAgent.jsx`)
- 工具函数: camelCase (如 `transcribeAudio`)
- 常量: UPPER_SNAKE_CASE
- CSS 类: kebab-case (如 `voice-input-button`)

### 文件组织

```
src/
├── components/     # 页面级组件
├── services/       # API 封装
├── styles/         # 样式文件
├── pictures/       # 图片资源
├── App.jsx         # 根组件
└── main.jsx        # 入口文件
```

## 性能优化

### 构建优化

- Vite 自动代码分割
- 懒加载大型组件
- 图片资源压缩

### 运行时优化

- 使用 React.memo 避免不必要渲染
- 使用 useMemo/useCallback 缓存计算
- 虚拟列表处理大量数据

### 语音输入优化

- 使用 useRef 解决闭包问题
- 录音计时器使用 setInterval
- 自动清理音频资源

## 浏览器兼容性

| 浏览器 | 最低版本 | 说明 |
|--------|----------|------|
| Chrome | 80+ | 完全支持 |
| Firefox | 75+ | 完全支持 |
| Safari | 14+ | 完全支持 |
| Edge | 80+ | 完全支持 |

**注意**: 语音输入功能需要浏览器支持 Web Audio API 和 MediaRecorder API。

## 常见问题

### Q: 语音输入无法使用？

A: 请检查：
1. 浏览器是否授予麦克风权限
2. 后端 ASR 服务是否正常运行
3. 是否使用 HTTPS (生产环境必需)

### Q: 语音识别准确率低？

A: 建议：
1. 在安静环境下使用
2. 说话清晰、语速适中
3. 使用标准普通话

### Q: 录音时长限制？

A: 单次录音最长 60 秒，超时自动停止。

### Q: 支持哪些语言？

A: 主要支持中文（简体）、英文、粤语，自动检测语言。

### Q: 地图加载失败？

A: 检查网络连接，确保能访问 Leaflet CDN。

## 更新日志

### v1.1.0 (2026-02-12)

- 新增语音输入功能
- AIAgent 组件支持语音转文字
- 集成 ASR 语音识别 API
- 优化录音按钮交互体验

### v1.0.0 (2026-02-08)

- 完成 React 前端架构
- 实现台风路径可视化
- 集成 AI 对话系统
- 完成图像分析功能
