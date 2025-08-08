# LLM推理服务前端

基于Framework7 + Vue.js 3的跨平台前端应用，支持桌面端、移动端和PWA。

## 项目结构

```
src/
├── components/          # Vue组件
│   └── common/         # 通用组件
│       ├── ErrorMessage.vue    # 错误消息组件
│       ├── LoadingSpinner.vue  # 加载动画组件
│       └── StatusBadge.vue     # 状态徽章组件
├── constants/          # 常量定义
│   └── index.ts       # 应用常量
├── pages/             # 页面组件
│   ├── Dashboard.vue  # 系统概览页面
│   ├── Models.vue     # 模型管理页面
│   ├── Monitoring.vue # 系统监控页面
│   └── Settings.vue   # 系统设置页面
├── services/          # API服务层
│   ├── api.ts         # 基础API客户端
│   ├── models.ts      # 模型管理API
│   └── monitoring.ts  # 监控API
├── stores/            # Pinia状态管理
│   ├── models.ts      # 模型状态存储
│   ├── monitoring.ts  # 监控状态存储
│   └── system.ts      # 系统状态存储
├── styles/            # 样式文件
│   ├── common.scss    # 通用样式
│   ├── desktop.scss   # 桌面端样式
│   └── mobile.scss    # 移动端样式
├── types/             # TypeScript类型定义
│   └── index.ts       # 应用类型
├── utils/             # 工具函数
│   └── index.ts       # 通用工具
├── App.vue            # 根组件
├── main.ts            # 应用入口
└── routes.ts          # 路由配置
```

## 技术栈

- **Framework7**: 跨平台UI框架
- **Vue.js 3**: 响应式前端框架
- **TypeScript**: 类型安全的JavaScript
- **Pinia**: Vue状态管理
- **Vite**: 构建工具
- **SCSS**: CSS预处理器

## 核心功能

### 1. 跨平台支持
- 桌面端：优化的大屏幕布局和交互
- 移动端：原生移动应用体验
- PWA：支持离线访问和桌面安装

### 2. 状态管理
- 模型管理状态（models store）
- 监控数据状态（monitoring store）
- 系统配置状态（system store）

### 3. API集成
- RESTful API客户端
- 自动错误处理和重试
- 请求/响应拦截器

### 4. 组件化设计
- 可复用的通用组件
- 响应式布局适配
- 统一的样式系统

## 开发指南

### 环境要求
- Node.js 18+
- npm 8+

### 安装依赖
```bash
npm install
```

### 开发模式
```bash
npm run dev          # 通用开发模式
npm run dev:desktop  # 桌面端开发模式
npm run dev:mobile   # 移动端开发模式
```

### 构建
```bash
npm run build        # 生产构建
npm run build:pwa    # PWA构建
npm run build:mobile # 移动端构建
npm run build:desktop # 桌面端构建
```

### 预览
```bash
npm run preview      # 预览构建结果
npm run preview:pwa  # 预览PWA版本
```

## 配置说明

### Framework7配置
- 自动主题检测（iOS/Android/Desktop）
- 响应式布局适配
- 触摸优化和手势支持

### PWA配置
- 离线缓存策略
- 桌面安装支持
- 后台同步

### 样式系统
- CSS变量定义
- 响应式断点
- 工具类样式

## API集成

### 后端接口
- 模型管理：`/api/models`
- 系统监控：`/api/system`
- WebSocket：`/ws`

### 状态同步
- 实时数据更新
- 自动重连机制
- 错误恢复处理

## 部署

### 静态部署
构建后的文件可部署到任何静态文件服务器。

### 反向代理
配置nginx代理API请求和WebSocket连接。

### PWA部署
确保HTTPS环境以启用PWA功能。