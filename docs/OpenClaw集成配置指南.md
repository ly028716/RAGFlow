# OpenClaw 集成配置指南

## 架构说明

正确的架构流程：
```
飞书 -> OpenClaw (WSL:18789) -> AI智能助手 (FastAPI:8000) -> RAG知识库
```

- **OpenClaw** 作为主入口，接收飞书消息
- **AI智能助手** 作为工具服务，提供知识库查询功能
- OpenClaw 的 Agent 通过调用 AI智能助手的 API 来查询知识库

## 配置步骤

### 1. 配置 AI智能助手

在 `backend/.env` 文件中添加：

```bash
# OpenClaw API Token（用于身份验证）
OPENCLAW_API_TOKENS=your-secret-token-here
```

可以配置多个 Token（逗号分隔）：
```bash
OPENCLAW_API_TOKENS=token1,token2,token3
```

### 2. 配置 OpenClaw 自定义工具

在 OpenClaw 的配置文件中注册 `query_knowledge_base` 工具：

```json
{
  "tools": {
    "custom": [
      {
        "name": "query_knowledge_base",
        "description": "查询 AI智能助手的 RAG 知识库，获取相关文档内容",
        "parameters": {
          "query": {
            "type": "string",
            "description": "查询内容",
            "required": true
          },
          "knowledge_base_ids": {
            "type": "array",
            "description": "知识库ID列表（可选，为空则查询所有知识库）",
            "items": {
              "type": "integer"
            }
          },
          "top_k": {
            "type": "integer",
            "description": "返回结果数量",
            "default": 5
          },
          "similarity_threshold": {
            "type": "number",
            "description": "相似度阈值（0.0-1.0）",
            "default": 0.7
          }
        },
        "endpoint": "http://host.docker.internal:8000/api/v1/tools/query-kb",
        "method": "POST",
        "headers": {
          "X-API-Token": "your-secret-token-here",
          "Content-Type": "application/json"
        }
      }
    ]
  }
}
```

**注意事项：**
- `endpoint` 使用 `host.docker.internal` 可以从 WSL 访问 Windows 主机
- 如果 AI智能助手也在 WSL 中运行，使用 `http://localhost:8000`
- `X-API-Token` 必须与 `.env` 中配置的 Token 一致

### 3. 配置飞书集成

在 OpenClaw 中配置飞书机器人，使其能够接收飞书消息。

具体配置方法请参考 OpenClaw 官方文档。

## API 端点说明

### POST /api/v1/tools/query-kb

查询知识库的 API 端点，供 OpenClaw 调用。

**请求头：**
```
X-API-Token: your-secret-token-here
Content-Type: application/json
```

**请求体：**
```json
{
  "query": "什么是 Python？",
  "knowledge_base_ids": [1, 2],
  "top_k": 5,
  "similarity_threshold": 0.7
}
```

**响应：**
```json
{
  "success": true,
  "query": "什么是 Python？",
  "results": [
    {
      "content": "Python 是一种高级编程语言...",
      "similarity_score": 0.92,
      "document_id": 1,
      "document_name": "Python 教程.pdf",
      "knowledge_base_id": 1,
      "knowledge_base_name": "技术文档"
    }
  ],
  "total_results": 5
}
```

## 测试

### 1. 测试 API 端点

```bash
curl -X POST http://localhost:8000/api/v1/tools/query-kb \
  -H "X-API-Token: your-secret-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "测试查询",
    "top_k": 3
  }'
```

### 2. 测试 OpenClaw 工具调用

在 OpenClaw 的聊天界面中发送消息：
```
请帮我查询知识库中关于 Python 的内容
```

OpenClaw 的 Agent 应该会自动调用 `query_knowledge_base` 工具。

## 故障排查

### 1. 401 Unauthorized

- 检查 `X-API-Token` 是否正确
- 检查 `.env` 中的 `OPENCLAW_API_TOKENS` 配置

### 2. 连接失败

- 检查 AI智能助手服务是否运行（http://localhost:8000）
- 检查网络连接（WSL 到 Windows 主机）
- 尝试使用 `host.docker.internal` 或 `localhost`

### 3. 404 Not Found

- 检查 API 端点路径是否正确：`/api/v1/tools/query-kb`
- 检查 AI智能助手服务是否正确启动

### 4. 知识库为空

- 确保已经上传文档到知识库
- 检查知识库 ID 是否正确
- 尝试不指定 `knowledge_base_ids`，查询所有知识库

## 使用流程

1. 用户通过飞书发送消息到 OpenClaw
2. OpenClaw 的 Agent 接收消息并分析
3. 如果需要查询知识库，Agent 调用 `query_knowledge_base` 工具
4. AI智能助手接收请求，执行 RAG 检索
5. 返回相关文档片段给 OpenClaw
6. OpenClaw 的 Agent 基于检索结果生成回答
7. 回答返回到飞书

## 安全建议

1. **API Token 管理**
   - 使用强随机字符串作为 Token
   - 定期更换 Token
   - 不要在代码中硬编码 Token

2. **网络安全**
   - 在生产环境中使用 HTTPS
   - 限制 API 访问的 IP 地址
   - 配置防火墙规则

3. **权限控制**
   - 为不同的 OpenClaw 实例配置不同的 Token
   - 记录所有 API 调用日志
   - 监控异常访问行为
