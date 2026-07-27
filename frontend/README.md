# RAGFlow 前端

Vue 3 + TypeScript + Element Plus 前端，用于演示本地知识库 RAG Agent 的上传、问答与可解释执行轨迹。

## 当前页面能力

- 登录与用户会话。
- 知识库和文档管理。
- 流式 RAG 对话与来源引用。
- `/agent` 调试台：选择授权知识库，展示改写查询、检索片段、最终上下文、引用校验、Token 和检索/生成/总耗时。

Agent 只运行受限的本地知识库链路，不暴露外部信息源或任意工具调用入口。

## 启动

```bash
npm install
npm run dev
```

开发环境默认将 `/api` 代理到 `http://localhost:8000`。如需覆盖：

```dotenv
VITE_API_BASE_URL=/api/v1
```

```bash
npm run test
npm run build
```

后端必须配置 DashScope API 密钥，并使用 `LLM_PROVIDER=dashscope`、`LLM_MODEL=qwen-plus`、`EMBEDDING_PROVIDER=dashscope` 和 `EMBEDDING_MODEL=text-embedding-v3`。完整演示路径见 [../docs/面试演示脚本.md](../docs/面试演示脚本.md)。
