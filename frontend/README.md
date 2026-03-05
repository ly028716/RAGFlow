# RAGFlow - 前端

基于 Vue 3 + TypeScript + Element Plus 的 RAGFlow 知识库问答系统前端。

## 技术栈

- **框架**: Vue 3 (Composition API)
- **语言**: TypeScript
- **构建工具**: Vite
- **UI 组件库**: Element Plus
- **状态管理**: Pinia
- **路由**: Vue Router 4
- **HTTP 客户端**: Axios
- **Markdown 渲染**: markdown-it + highlight.js

## 功能模块

- ✅ 用户认证（登录/注册）
- ✅ 智能对话（流式输出）
- ✅ 对话历史管理
- 🚧 知识库管理
- 🚧 Agent 工具
- ✅ 个人设置

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产版本
npm run preview
```

## 项目结构

```
src/
├── api/           # API 接口封装
├── components/    # 公共组件
│   └── chat/      # 对话相关组件
├── composables/   # 组合式函数
├── layouts/       # 布局组件
├── router/        # 路由配置
├── stores/        # Pinia 状态管理
├── styles/        # 全局样式
├── types/         # TypeScript 类型定义
├── utils/         # 工具函数
└── views/         # 页面组件
```

## 环境变量

创建 `.env` 文件：

```bash
VITE_API_BASE_URL=/api/v1
```

## 开发说明

- 开发环境下，Vite 会将 `/api` 请求代理到 `http://localhost:8000`
- 确保后端服务已启动
