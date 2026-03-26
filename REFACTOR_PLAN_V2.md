# RAGFlow + OpenClaw 集成重构方案 V2.0

**基于OpenClaw 2026.3.3最新代码**

---

## 📋 执行摘要

本方案将RAGFlow知识库系统与OpenClaw个人AI助手集成，实现飞书→OpenClaw→RAGFlow的消息流转架构。

**核心理念**：
- OpenClaw负责消息路由、Agent运行、多渠道管理
- RAGFlow专注于知识库管理和RAG功能
- 通过OpenClaw Skill解耦两个系统

**预计时间**：5-7天

---

## 🎯 架构设计

### 当前架构（问题）

```
飞书 → RAGFlow后端(/api/v1/feishu) → RAG/Agent（直接）
```

**问题**：
- 飞书直接对接RAGFlow，绕过了OpenClaw
- 无法利用OpenClaw的多渠道能力
- 未来接入其他渠道需要重复开发

### 目标架构（优化）

```
飞书/钉钉/企业微信
    ↓
OpenClaw Gateway (/hooks/feishu)
    ↓
OpenClaw Agent (AI处理)
    ↓
使用Skill: ragflow-kb
    ↓
HTTP调用 → RAGFlow (/api/v1/tools/query-kb)
    ↓
返回知识库结果
    ↓
OpenClaw Agent生成最终响应
    ↓
OpenClaw Gateway
    ↓
飞书/钉钉/企业微信
```

**优势**：
- ✅ OpenClaw统一管理所有消息渠道
- ✅ RAGFlow专注于知识库功能
- ✅ 通过Skill解耦，易于扩展
- ✅ 可复用RAGFlow现有工具接口
- ✅ 支持多渠道（飞书、钉钉、企业微信等）

---

## 🔧 实施阶段

### Phase 1: RAGFlow工具接口优化（1-2天）

**目标**：优化RAGFlow的工具接口，使其更适合OpenClaw调用

#### 1.1 优化现有工具接口

**文件**：`backend/app/api/v1/tools.py`

**任务**：
- [ ] 检查现有`/api/v1/tools/query-kb`接口
- [ ] 优化响应格式，确保返回结构化数据
- [ ] 添加API Token认证（用于OpenClaw调用）
- [ ] 添加请求日志和监控

**接口规范**：
```python
POST /api/v1/tools/query-kb
Headers:
  X-API-Token: <token>
  Content-Type: application/json

Request:
{
  "query": "查询内容",
  "kb_id": 1,  # 可选，指定知识库
  "top_k": 5,  # 可选，返回结果数量
  "user_id": 123  # 可选，用户ID
}

Response:
{
  "success": true,
  "results": [
    {
      "content": "文档内容片段",
      "score": 0.95,
      "metadata": {
        "source": "doc1.pdf",
        "page": 3
      }
    }
  ],
  "execution_time": 0.5
}
```

#### 1.2 添加API Token认证

**文件**：`backend/app/config.py`

**任务**：
- [ ] 添加`OPENCLAW_API_TOKENS`配置
- [ ] 支持多个token（逗号分隔）

**配置示例**：
```python
class OpenClawSettings(BaseSettings):
    api_tokens: str = Field(
        default="",
        description="OpenClaw API Token列表（逗号分隔）"
    )
```

**文件**：`backend/app/dependencies.py`

**任务**：
- [ ] 创建`verify_openclaw_token`依赖
- [ ] 验证`X-API-Token`头

**代码示例**：
```python
async def verify_openclaw_token(
    api_token: str = Header(..., alias="X-API-Token")
) -> bool:
    """验证OpenClaw API Token"""
    valid_tokens = settings.openclaw.api_tokens.split(",")
    valid_tokens = [t.strip() for t in valid_tokens if t.strip()]

    if not valid_tokens or api_token not in valid_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Token"
        )
    return True
```

#### 1.3 测试工具接口

**任务**：
- [ ] 编写单元测试
- [ ] 测试API Token认证
- [ ] 测试查询功能
- [ ] 测试错误处理

---

### Phase 2: 创建OpenClaw Skill（2-3天）

**目标**：创建一个OpenClaw Skill，教agent如何查询RAGFlow知识库

#### 2.1 创建Skill目录结构

**位置**：`~/.openclaw/workspace/skills/ragflow-kb/`

**文件结构**：
```
ragflow-kb/
├── SKILL.md           # Skill定义
├── query.sh           # 查询脚本（可选）
└── README.md          # 说明文档
```

#### 2.2 编写SKILL.md

**文件**：`~/.openclaw/workspace/skills/ragflow-kb/SKILL.md`

**内容**：
```markdown
---
name: ragflow_kb
description: Query RAGFlow knowledge base for relevant documents and information
metadata: {"openclaw": {"requires": {"env": ["RAGFLOW_API_URL", "RAGFLOW_API_TOKEN"]}, "primaryEnv": "RAGFLOW_API_TOKEN"}}
---

# RAGFlow Knowledge Base Query

This skill allows you to query the RAGFlow knowledge base system to retrieve relevant documents and information.

## When to use this skill

Use this skill when:
- User asks questions that require knowledge base lookup
- User wants to search for specific information in documents
- User needs context from uploaded documents

## How to use

To query the RAGFlow knowledge base, use the `exec` tool with the following command:

```bash
curl -X POST "${RAGFLOW_API_URL}/api/v1/tools/query-kb" \
  -H "X-API-Token: ${RAGFLOW_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "<user_query>",
    "top_k": 5
  }'
```

Replace `<user_query>` with the actual user question.

## Response format

The API returns JSON with the following structure:
- `success`: boolean indicating if the query was successful
- `results`: array of relevant document chunks
  - `content`: the text content
  - `score`: relevance score (0-1)
  - `metadata`: source information (file name, page number, etc.)
- `execution_time`: query execution time in seconds

## Example

User: "What is the company's vacation policy?"

You should:
1. Use the `exec` tool to call the RAGFlow API with query "company vacation policy"
2. Parse the JSON response
3. Synthesize the information from the top results
4. Provide a clear answer to the user, citing sources when appropriate

## Important notes

- Always check if `success` is true before processing results
- If no results are found, inform the user politely
- Cite sources when providing information (e.g., "According to doc1.pdf, page 3...")
- If the API returns an error, explain the issue to the user
```

#### 2.3 配置OpenClaw环境变量

**文件**：`~/.openclaw/.env` 或 OpenClaw配置

**任务**：
- [ ] 添加`RAGFLOW_API_URL`环境变量
- [ ] 添加`RAGFLOW_API_TOKEN`环境变量

**示例**：
```bash
RAGFLOW_API_URL=http://localhost:8000
RAGFLOW_API_TOKEN=your-secure-token-here
```

#### 2.4 测试Skill

**任务**：
- [ ] 重启OpenClaw Gateway
- [ ] 验证Skill已加载：`openclaw agent --message "list skills"`
- [ ] 测试查询：`openclaw agent --message "查询知识库中关于产品的信息"`
- [ ] 验证响应正确

---

### Phase 3: 配置飞书Webhook（1-2天）

**目标**：配置OpenClaw接收飞书webhook消息

#### 3.1 配置OpenClaw Webhook

**文件**：`~/.openclaw/openclaw.json`

**任务**：
- [ ] 启用webhook功能
- [ ] 配置飞书webhook映射
- [ ] 设置消息路由

**配置示例**：
```json5
{
  hooks: {
    enabled: true,
    token: "${OPENCLAW_HOOKS_TOKEN}",  // 从环境变量读取
    path: "/hooks",

    // 飞书webhook映射
    mappings: [
      {
        name: "feishu",
        match: {
          path: "/feishu",
          method: "POST"
        },
        action: "agent",
        transform: {
          // 消息格式转换
          message: "$.event.message.content.text",
          name: "Feishu",
          agentId: "main",
          deliver: true,
          channel: "last",  // 或指定具体渠道
          wakeMode: "now"
        }
      }
    ]
  }
}
```

#### 3.2 创建消息转换脚本（可选）

如果需要复杂的消息格式转换，可以创建自定义transform模块。

**文件**：`~/.openclaw/hooks/transforms/feishu-transform.ts`

**任务**：
- [ ] 解析飞书消息格式
- [ ] 提取文本内容
- [ ] 转换为OpenClaw消息格式

**代码示例**：
```typescript
export function transform(payload: any) {
  const event = payload.event || {};
  const message = event.message || {};
  const content = message.content || {};

  // 提取文本内容
  let text = "";
  if (message.message_type === "text") {
    text = JSON.parse(content).text || "";
  }

  return {
    message: text,
    name: "Feishu",
    agentId: "main",
    deliver: true,
    channel: "last",
    wakeMode: "now"
  };
}
```

#### 3.3 配置飞书应用

**任务**：
- [ ] 在飞书开放平台创建应用
- [ ] 配置事件订阅URL：`https://your-domain/hooks/feishu`
- [ ] 订阅"接收消息"事件
- [ ] 配置Verification Token和Encrypt Key
- [ ] 测试webhook连接

---

### Phase 4: 集成测试与优化（1-2天）

**目标**：端到端测试整个流程，优化性能和用户体验

#### 4.1 端到端测试

**测试场景**：

1. **基础查询测试**
   - [ ] 飞书发送消息："查询产品文档"
   - [ ] 验证OpenClaw接收消息
   - [ ] 验证Skill被调用
   - [ ] 验证RAGFlow返回结果
   - [ ] 验证OpenClaw生成响应
   - [ ] 验证飞书收到回复

2. **多轮对话测试**
   - [ ] 测试上下文保持
   - [ ] 测试多次查询
   - [ ] 验证会话管理

3. **错误处理测试**
   - [ ] RAGFlow API不可用
   - [ ] 知识库为空
   - [ ] 查询超时
   - [ ] 验证错误提示友好

4. **性能测试**
   - [ ] 测试响应时间（目标<3秒）
   - [ ] 测试并发请求
   - [ ] 验证系统稳定性

#### 4.2 性能优化

**任务**：
- [ ] 优化RAGFlow查询性能
- [ ] 添加缓存机制（可选）
- [ ] 优化OpenClaw Skill提示词
- [ ] 减少不必要的API调用

#### 4.3 监控与日志

**任务**：
- [ ] 添加Prometheus指标
  - `ragflow_kb_queries_total`：查询总数
  - `ragflow_kb_query_duration_seconds`：查询耗时
  - `ragflow_kb_errors_total`：错误数
- [ ] 配置日志收集
- [ ] 设置告警规则

---

### Phase 5: 文档与部署（1天）

**目标**：编写文档，准备生产部署

#### 5.1 编写用户文档

**文件**：`docs/integration/openclaw-feishu.md`

**内容**：
- [ ] 架构说明
- [ ] 配置指南
- [ ] 使用说明
- [ ] 故障排查
- [ ] FAQ

#### 5.2 编写部署文档

**文件**：`docs/deployment/openclaw-deployment.md`

**内容**：
- [ ] 环境要求
- [ ] 安装步骤
- [ ] 配置说明
- [ ] 启动命令
- [ ] 健康检查

#### 5.3 更新CLAUDE.md

**文件**：`CLAUDE.md`

**任务**：
- [ ] 添加OpenClaw集成说明
- [ ] 更新架构图
- [ ] 添加常用命令

---

## 📊 关键文件清单

### RAGFlow后端

**新增/修改**：
```
backend/app/config.py                           # 添加OpenClaw配置
backend/app/dependencies.py                     # 添加token验证
backend/app/api/v1/tools.py                     # 优化工具接口
backend/tests/api/v1/test_tools.py              # 测试
docs/integration/openclaw-feishu.md             # 集成文档
docs/deployment/openclaw-deployment.md          # 部署文档
```

### OpenClaw配置

**新增**：
```
~/.openclaw/workspace/skills/ragflow-kb/SKILL.md    # Skill定义
~/.openclaw/openclaw.json                           # Webhook配置
~/.openclaw/.env                                    # 环境变量
~/.openclaw/hooks/transforms/feishu-transform.ts    # 消息转换（可选）
```

---

## ⚠️ 重要注意事项

### 1. 安全性

- [ ] **API Token管理**：使用强随机token，定期轮换
- [ ] **HTTPS**：生产环境必须使用HTTPS
- [ ] **限流**：配置合理的限流策略
- [ ] **日志脱敏**：避免记录敏感信息

### 2. 性能

- [ ] **响应时间**：目标端到端<3秒
- [ ] **并发处理**：支持至少10个并发请求
- [ ] **资源限制**：配置合理的超时和重试

### 3. 可靠性

- [ ] **错误处理**：所有错误都应有友好提示
- [ ] **降级方案**：RAGFlow不可用时的备用方案
- [ ] **监控告警**：关键指标异常时及时告警

### 4. 可维护性

- [ ] **文档完整**：所有配置都有说明
- [ ] **日志清晰**：便于问题排查
- [ ] **版本管理**：记录配置变更历史

---

## 🎯 验收标准

### 功能验收

- [ ] 飞书消息能通过OpenClaw正常转发到RAGFlow
- [ ] RAGFlow知识库查询正常工作
- [ ] OpenClaw Agent能正确使用Skill
- [ ] 响应能正常返回到飞书
- [ ] 多轮对话上下文保持正常

### 性能验收

- [ ] 端到端响应时间<3秒（P95）
- [ ] 系统吞吐量>10 QPS
- [ ] 错误率<1%

### 安全验收

- [ ] API Token认证正常工作
- [ ] 飞书签名验证正常工作
- [ ] 敏感信息不泄露

---

## 📈 后续优化

重构完成后，可以考虑以下优化：

1. **接入更多渠道**
   - 钉钉
   - 企业微信
   - Slack
   - Discord

2. **增强Skill功能**
   - 支持指定知识库查询
   - 支持文档上传
   - 支持多模态查询（图片、语音）

3. **性能优化**
   - 添加查询缓存
   - 优化向量检索
   - 使用连接池

4. **用户体验优化**
   - 添加查询进度提示
   - 支持流式响应
   - 添加引用来源链接

---

## 🚀 快速开始

### 最小可行配置

**1. 配置RAGFlow**

```bash
cd backend
# 添加环境变量
echo "OPENCLAW_API_TOKENS=your-secure-token-here" >> .env
# 重启服务
uvicorn app.main:app --reload
```

**2. 配置OpenClaw**

```bash
# 创建Skill目录
mkdir -p ~/.openclaw/workspace/skills/ragflow-kb

# 创建SKILL.md（使用上面的模板）
cat > ~/.openclaw/workspace/skills/ragflow-kb/SKILL.md << 'EOF'
---
name: ragflow_kb
description: Query RAGFlow knowledge base
metadata: {"openclaw": {"requires": {"env": ["RAGFLOW_API_URL", "RAGFLOW_API_TOKEN"]}}}
---
# RAGFlow Knowledge Base Query
[... 完整内容见上面的模板 ...]
EOF

# 配置环境变量
cat >> ~/.openclaw/.env << EOF
RAGFLOW_API_URL=http://localhost:8000
RAGFLOW_API_TOKEN=your-secure-token-here
OPENCLAW_HOOKS_TOKEN=your-hooks-token-here
EOF

# 配置webhook
cat > ~/.openclaw/openclaw.json << 'EOF'
{
  "hooks": {
    "enabled": true,
    "token": "${OPENCLAW_HOOKS_TOKEN}",
    "path": "/hooks",
    "mappings": [
      {
        "name": "feishu",
        "match": {"path": "/feishu", "method": "POST"},
        "action": "agent",
        "transform": {
          "message": "$.event.message.content.text",
          "name": "Feishu",
          "deliver": true
        }
      }
    ]
  }
}
EOF

# 重启OpenClaw
openclaw gateway restart
```

**3. 测试**

```bash
# 测试RAGFlow工具接口
curl -X POST http://localhost:8000/api/v1/tools/query-kb \
  -H "X-API-Token: your-secure-token-here" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 5}'

# 测试OpenClaw Skill
openclaw agent --message "查询知识库中关于产品的信息"

# 测试飞书webhook（需要配置飞书应用）
curl -X POST http://localhost:18789/hooks/feishu \
  -H "Authorization: Bearer your-hooks-token-here" \
  -H "Content-Type: application/json" \
  -d '{"event": {"message": {"content": {"text": "测试消息"}}}}'
```

---

## 📞 支持与反馈

如有问题，请：
1. 查看文档：`docs/integration/openclaw-feishu.md`
2. 查看日志：`openclaw logs --follow`
3. 运行诊断：`openclaw doctor`
4. 提交Issue到项目仓库

---

## 📝 总结

本重构方案将RAGFlow与OpenClaw集成，实现了：
- ✅ 统一的消息网关（OpenClaw）
- ✅ 专注的知识库服务（RAGFlow）
- ✅ 灵活的Skill扩展机制
- ✅ 多渠道支持能力

**预计时间**：5-7天
**关键成功因素**：
1. 充分测试
2. 完善文档
3. 监控告警
4. 用户培训

**下一步行动**：
1. 评审本方案
2. 准备开发环境
3. 开始Phase 1实施
