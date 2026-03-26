# Phase 3 实施计划：配置飞书Webhook

## 目标
配置OpenClaw接收飞书webhook消息，并通过RAGFlow Skill查询知识库。

## 实施策略

### 阶段1：本地测试（优先）
1. 配置OpenClaw webhook基础功能
2. 使用curl模拟飞书消息
3. 验证消息处理流程
4. 测试RAGFlow Skill调用

### 阶段2：飞书集成（后续）
1. 研究飞书响应机制
2. 配置飞书应用
3. 端到端测试

## 当前状态

### 已完成
- ✅ RAGFlow工具接口（Phase 1）
- ✅ OpenClaw Skill创建（Phase 2）
- ✅ 环境变量配置

### 待完成
- ⚠️ OpenClaw Gateway启动
- ⚠️ Webhook配置
- ⚠️ 本地测试

## 实施步骤

### Step 1: 配置RAGFlow API Token

在RAGFlow后端配置OpenClaw API Token：

```bash
# backend/.env
OPENCLAW_API_TOKENS=test-openclaw-token-12345
```

### Step 2: 配置OpenClaw环境变量

更新 `~/.openclaw/.env`：

```bash
RAGFLOW_API_URL=http://localhost:8000
RAGFLOW_API_TOKEN=test-openclaw-token-12345
OPENCLAW_HOOKS_TOKEN=test-hooks-token-67890
OPENCLAW_GATEWAY_TOKEN=test-gateway-token-1772761987
```

### Step 3: 测试RAGFlow工具接口

```bash
curl -X POST http://localhost:8000/api/v1/tools/query-kb \
  -H "X-API-Token: test-openclaw-token-12345" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 5}'
```

### Step 4: 启动OpenClaw Gateway

```bash
openclaw gateway --port 18789
```

### Step 5: 测试OpenClaw Skill

```bash
# 设置环境变量
export RAGFLOW_API_URL=http://localhost:8000
export RAGFLOW_API_TOKEN=test-openclaw-token-12345

# 测试agent
openclaw agent --message "查询知识库中关于产品的信息"
```

### Step 6: 配置Webhook（简化版）

由于OpenClaw的webhook配置较复杂，我们先使用`/hooks/agent`端点进行测试：

```bash
curl -X POST http://localhost:18789/hooks/agent \
  -H "Authorization: Bearer test-hooks-token-67890" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查询知识库中关于Python的信息",
    "name": "Test",
    "agentId": "main",
    "deliver": false,
    "wakeMode": "now"
  }'
```

## 注意事项

1. **响应机制未解决**：当前方案暂不处理响应返回飞书的问题
2. **需要手动测试**：OpenClaw Gateway需要手动启动和测试
3. **Token配置**：确保所有token配置一致

## 下一步

完成本地测试后，再研究飞书响应机制和完整集成。
