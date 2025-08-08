---
inclusion: always
---

# 项目结构规范

## 根目录布局
```
llm-inference-service/
├── backend/                 # FastAPI后端服务
├── frontend/               # Vue.js Web界面
├── docker/                 # Docker配置文件
├── scripts/                # 部署和工具脚本
├── docs/                   # 项目文档
├── tests/                  # 测试套件
├── configs/                # 配置模板
└── .kiro/                  # Kiro AI助手文件
```

## 后端结构 (`backend/`)
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI应用程序入口
│   ├── api/               # REST API端点
│   │   ├── __init__.py
│   │   ├── models.py      # 模型管理端点
│   │   ├── monitoring.py  # 系统监控端点
│   │   └── system.py      # 系统配置端点
│   ├── core/              # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── config.py      # 应用程序配置
│   │   ├── database.py    # 数据库连接
│   │   └── security.py    # 认证/授权
│   ├── services/          # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── model_manager.py     # 模型生命周期管理
│   │   ├── resource_scheduler.py # GPU资源调度
│   │   ├── monitoring.py        # 系统监控
│   │   └── config_manager.py    # 配置管理
│   ├── adapters/          # 框架适配器
│   │   ├── __init__.py
│   │   ├── base.py        # 抽象适配器接口
│   │   ├── llama_cpp.py   # llama.cpp适配器
│   │   ├── vllm.py        # vLLM适配器
│   │   └── docker.py      # Docker容器适配器
│   ├── models/            # 数据模型和模式
│   │   ├── __init__.py
│   │   ├── database.py    # SQLAlchemy模型
│   │   ├── schemas.py     # Pydantic模式
│   │   └── enums.py       # 枚举类型
│   └── utils/             # 工具函数
│       ├── __init__.py
│       ├── gpu.py         # GPU检测和监控
│       ├── logging.py     # 日志配置
│       └── helpers.py     # 通用工具
├── requirements.txt       # Python依赖
├── requirements-dev.txt   # 开发依赖
└── alembic/              # 数据库迁移
```

## 前端结构 (`frontend/`)
```
frontend/
├── src/                  # Framework7 + Vue.js统一应用
│   ├── main.ts          # 应用程序入口
│   ├── App.vue          # 根组件
│   ├── routes.ts        # Framework7路由配置
│   ├── stores/          # Pinia状态管理
│   │   ├── models.ts    # 模型管理状态
│   │   ├── monitoring.ts # 监控数据状态
│   │   └── system.ts    # 系统配置状态
│   ├── components/      # Framework7组件
│   │   ├── common/      # 通用UI组件
│   │   ├── models/      # 模型相关组件
│   │   ├── monitoring/  # 监控组件
│   │   ├── desktop/     # 桌面端特定组件
│   │   └── mobile/      # 移动端特定组件
│   ├── pages/           # Framework7页面
│   │   ├── Dashboard.vue # 主仪表板
│   │   ├── Models.vue   # 模型管理
│   │   ├── Monitoring.vue # 系统监控
│   │   └── Settings.vue # 配置设置
│   ├── services/        # API服务层
│   │   ├── api.ts       # 基础API客户端
│   │   ├── models.ts    # 模型API调用
│   │   └── monitoring.ts # 监控API调用
│   ├── types/           # TypeScript类型定义
│   ├── utils/           # 通用工具函数
│   ├── constants/       # 常量定义
│   └── styles/          # 样式文件
│       ├── desktop.scss # 桌面端样式
│       ├── mobile.scss  # 移动端样式
│       └── common.scss  # 通用样式
├── public/              # 静态资源
│   ├── icons/          # 应用图标
│   ├── manifest.json   # PWA清单
│   └── sw.js          # Service Worker
├── package.json         # 依赖管理
├── vite.config.ts      # Vite配置
└── tsconfig.json       # TypeScript配置
```

## 配置结构 (`configs/`)
```
configs/
├── development.yaml      # 开发环境配置
├── production.yaml       # 生产环境配置
├── docker-compose.yml    # Docker服务配置
├── nginx.conf           # Nginx反向代理配置
└── systemd/             # systemd服务文件
    └── llm-inference-service.service
```

## 核心架构模式

### 服务层模式
- `backend/app/services/`中的服务包含业务逻辑
- 每个服务处理特定领域（模型、监控、调度）
- 服务作为依赖注入到API端点中

### 适配器模式
- `backend/app/adapters/`中的框架适配器提供统一接口
- 每个适配器为不同AI框架实现相同的基础接口
- 允许轻松添加新框架而不改变核心逻辑

### 仓储模式
- 通过仓储类抽象数据库操作
- 配置和模型状态持久化处理一致
- 易于切换数据库后端（SQLite ↔ PostgreSQL）

### 组件化前端
- Vue.js组件按功能域组织
- `common/`中的共享组件提高复用性
- 状态管理集中在Pinia存储中

### Framework7统一架构模式
- **统一框架**: Framework7 + Vue.js提供跨平台一致性体验
- **主题自适应**: 自动检测设备类型并应用对应主题（iOS/Android/Desktop）
- **组件复用**: 同一套组件在不同平台自动适配样式和交互
- **响应式布局**: CSS媒体查询实现不同屏幕尺寸的优化显示
- **PWA增强**: 支持离线缓存和原生应用体验

## 文件命名约定
- **Python文件**: snake_case（如：`model_manager.py`）
- **Vue组件**: PascalCase（如：`ModelCard.vue`）
- **TypeScript文件**: camelCase（如：`apiClient.ts`）
- **配置文件**: kebab-case（如：`docker-compose.yml`）
- **数据库模型**: PascalCase类名，snake_case表名
- **API端点**: kebab-case URL（如：`/api/model-configs`）

## 导入组织规范
- 标准库导入在最前面
- 第三方库导入在中间
- 本地应用导入在最后
- 优先使用绝对导入而非相对导入
- 按功能分组导入，用空行分隔

## 代码组织原则
- 单一职责：每个模块只负责一个功能
- 依赖注入：通过构造函数注入依赖
- 接口隔离：定义清晰的接口边界
- 配置外部化：将配置与代码分离
- 错误处理：统一的异常处理机制